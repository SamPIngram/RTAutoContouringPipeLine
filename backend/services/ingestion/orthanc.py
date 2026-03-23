import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class OrthancStudyInfo:
    study_id: str
    patient_id: str
    study_uid: str
    modality: str
    series_description: str | None
    dicom_dir: str | None = None


class OrthancService:
    """Client for the Orthanc REST API."""

    def __init__(self, url: str, username: str, password: str) -> None:
        self._base_url = url.rstrip("/")
        self._auth = (username, password)

    def _client(self) -> httpx.Client:
        return httpx.Client(auth=self._auth, timeout=30)

    def get_study_info(self, orthanc_study_id: str) -> OrthancStudyInfo:
        with self._client() as client:
            resp = client.get(f"{self._base_url}/studies/{orthanc_study_id}")
            resp.raise_for_status()
            data = resp.json()

        patient_main = data.get("PatientMainDicomTags", {})
        study_main = data.get("MainDicomTags", {})

        return OrthancStudyInfo(
            study_id=orthanc_study_id,
            patient_id=patient_main.get("PatientID", "UNKNOWN"),
            study_uid=study_main.get("StudyInstanceUID", orthanc_study_id),
            modality=data.get("RequestedTags", {}).get("Modality", "OT"),
            series_description=study_main.get("SeriesDescription"),
        )

    def download_study_dicom(self, orthanc_study_id: str, dest_dir: str) -> str:
        """Download the study as a DICOM archive to dest_dir.

        Returns the path to the extracted directory.
        """
        import io
        import zipfile
        from pathlib import Path

        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)

        with self._client() as client:
            resp = client.get(f"{self._base_url}/studies/{orthanc_study_id}/archive")
            resp.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            zf.extractall(dest)

        logger.info("DICOM study downloaded", extra={"orthanc_id": orthanc_study_id, "dest": str(dest)})
        return str(dest)

    def send_file(self, file_path: str) -> str:
        """Upload a DICOM file to Orthanc. Returns the Orthanc instance ID."""
        from pathlib import Path

        with self._client() as client:
            with open(file_path, "rb") as f:
                resp = client.post(
                    f"{self._base_url}/instances",
                    content=f.read(),
                    headers={"Content-Type": "application/dicom"},
                )
            resp.raise_for_status()
            instance_id: str = resp.json()["ID"]

        logger.info("DICOM file sent to Orthanc", extra={"file": Path(file_path).name, "instance_id": instance_id})
        return instance_id
