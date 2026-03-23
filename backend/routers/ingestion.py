import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


class OrthancWebhookPayload(BaseModel):
    ResourceType: str
    ResourceId: str
    ChangeType: str | None = None


class FolderIngestRequest(BaseModel):
    folder_path: str
    recursive: bool = True


class ProKnowIngestRequest(BaseModel):
    workspace: str
    patient_id: str | None = None


@router.post("/orthanc/webhook", summary="Receive Orthanc change webhook")
async def orthanc_webhook(
    payload: OrthancWebhookPayload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Called by Orthanc when a new instance or stable study is detected."""
    from backend.tasks.conversion import convert_dicom_to_nifti

    logger.info(
        "Orthanc webhook received",
        extra={"resource_type": payload.ResourceType, "resource_id": payload.ResourceId},
    )

    if payload.ResourceType == "Study":
        background_tasks.add_task(
            convert_dicom_to_nifti.delay,
            orthanc_study_id=payload.ResourceId,
            import_source="orthanc_webhook",
        )

    return {"status": "accepted", "resource_id": payload.ResourceId}


@router.post("/ingest/folder", summary="Trigger ingestion from a local folder")
async def ingest_folder(
    request: FolderIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Enqueue a folder-watch ingestion job."""
    from backend.tasks.conversion import convert_dicom_to_nifti

    task = convert_dicom_to_nifti.delay(
        folder_path=request.folder_path,
        recursive=request.recursive,
        import_source="folder_watch",
    )
    logger.info("Folder ingest task enqueued", extra={"task_id": task.id})
    return {"status": "queued", "task_id": task.id}


@router.post("/ingest/proknow", summary="Trigger ProKnow sync")
async def ingest_proknow(
    request: ProKnowIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Enqueue a ProKnow sync job."""
    from backend.tasks.conversion import convert_dicom_to_nifti

    task = convert_dicom_to_nifti.delay(
        proknow_workspace=request.workspace,
        proknow_patient_id=request.patient_id,
        import_source="proknow_sync",
    )
    logger.info("ProKnow sync task enqueued", extra={"task_id": task.id})
    return {"status": "queued", "task_id": task.id}
