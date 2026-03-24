import logging

logger = logging.getLogger(__name__)


class ProKnowSync:
    """Periodic pull from ProKnow SDK.

    Fetches patient data from a configured ProKnow workspace and enqueues
    DICOM-to-NIfTI conversion tasks for any new studies found.

    Requires the `proknow` package and valid API credentials configured in
    the [proknow] section of config.toml.
    """

    def __init__(self, base_url: str, credentials_file: str) -> None:
        self._base_url = base_url
        self._credentials_file = credentials_file

    def sync_workspace(self, workspace: str, patient_id: str | None = None) -> list[str]:
        """Pull studies from a ProKnow workspace.

        Returns a list of study UIDs that were queued for conversion.
        """
        if not self._base_url or not self._credentials_file:
            logger.warning("ProKnow not configured — skipping sync.")
            return []

        try:
            from proknow import ProKnow  # type: ignore[import]
        except ImportError:
            logger.error("proknow package not installed. Run: uv add proknow")
            return []

        pk = ProKnow(self._base_url, credentials_file=self._credentials_file)
        ws = pk.workspaces.find(name=workspace)

        patients = pk.patients.query(ws.id, search=patient_id or "")
        queued: list[str] = []

        for patient_summary in patients:
            patient = patient_summary.get()
            for entity in patient.find_entities(lambda e: e.type == "image_set"):
                study_uid = entity.data.get("study_instance_uid", entity.id)
                from backend.tasks.conversion import convert_dicom_to_nifti
                convert_dicom_to_nifti.delay(
                    proknow_workspace=workspace,
                    proknow_patient_id=patient.data["mrn"],
                    import_source="proknow_sync",
                )
                queued.append(study_uid)

        logger.info(
            "ProKnow sync complete",
            extra={"workspace": workspace, "queued_count": len(queued)},
        )
        return queued
