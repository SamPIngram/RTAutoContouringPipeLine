import logging

from backend.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="backend.tasks.conversion.convert_dicom_to_nifti", bind=True)
def convert_dicom_to_nifti(
    self,
    orthanc_study_id: str | None = None,
    folder_path: str | None = None,
    recursive: bool = True,
    proknow_workspace: str | None = None,
    proknow_patient_id: str | None = None,
    import_source: str = "unknown",
) -> dict:
    """Convert a DICOM study to NIfTI format.

    Supports three ingestion modes:
    - orthanc_study_id: pull from the Orthanc instance
    - folder_path: read from a local/network directory
    - proknow_workspace: sync from ProKnow
    """
    from backend.services.preprocessing.conversion import DicomToNiftiConverter

    logger.info(
        "Starting DICOM-to-NIfTI conversion",
        extra={"import_source": import_source, "orthanc_study_id": orthanc_study_id},
    )

    converter = DicomToNiftiConverter()

    if orthanc_study_id:
        result = converter.convert_from_orthanc(orthanc_study_id)
    elif folder_path:
        result = converter.convert_from_folder(folder_path, recursive=recursive)
    elif proknow_workspace:
        result = converter.convert_from_proknow(proknow_workspace, proknow_patient_id)
    else:
        raise ValueError("One of orthanc_study_id, folder_path, or proknow_workspace is required.")

    logger.info("DICOM-to-NIfTI conversion complete", extra={"result": result})
    return result
