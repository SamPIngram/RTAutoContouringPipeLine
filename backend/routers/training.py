import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


class TrainingRequest(BaseModel):
    dataset_id: int
    model_name: str
    framework: str = "nnunet"
    gpu_index: int | None = None
    extra_config: dict = Field(default_factory=dict)


class TrainingStatusResponse(BaseModel):
    job_id: str
    status: str
    result: dict | None = None


@router.post("/training/start", summary="Start a training job")
async def start_training(
    request: TrainingRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Enqueue a training job. Heavy work runs in an ephemeral Docker container."""
    from backend.tasks.training import run_training_job

    task = run_training_job.delay(
        dataset_id=request.dataset_id,
        model_name=request.model_name,
        framework=request.framework,
        gpu_index=request.gpu_index,
        extra_config=request.extra_config,
    )
    logger.info(
        "Training job enqueued",
        extra={"task_id": task.id, "dataset_id": request.dataset_id},
    )
    return {"status": "queued", "job_id": task.id}


@router.get(
    "/training/{job_id}/status",
    response_model=TrainingStatusResponse,
    summary="Get training job status",
)
async def get_training_status(job_id: str) -> TrainingStatusResponse:
    from backend.celery_app import app as celery_app

    result = celery_app.AsyncResult(job_id)
    state = result.state

    if state == "FAILURE":
        raise HTTPException(status_code=500, detail=str(result.result))

    return TrainingStatusResponse(
        job_id=job_id,
        status=state,
        result=result.result if state == "SUCCESS" else None,
    )
