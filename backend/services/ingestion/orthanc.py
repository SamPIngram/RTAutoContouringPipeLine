import logging
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

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

        Streams the archive to a temporary file to avoid loading the entire
        archive into memory, then extracts it in place.

        Returns the path to the extracted directory.
        """
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)

        with self._client() as client:
            # Stream response to a temp file — DICOM archives can be several GB
            with client.stream(
                "GET", f"{self._base_url}/studies/{orthanc_study_id}/archive"
            ) as resp:
                resp.raise_for_status()
                with tempfile.TemporaryFile() as tmp:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        tmp.write(chunk)
                    tmp.seek(0)
                    with zipfile.ZipFile(tmp) as zf:
                        zf.extractall(dest)

        logger.info(
            "DICOM study downloaded",
            extra={"orthanc_id": orthanc_study_id, "dest": str(dest)},
        )
        return str(dest)

    def send_file(self, file_path: str) -> str:
        """Upload a DICOM file to Orthanc. Returns the Orthanc instance ID.

        Streams the file in chunks to avoid loading the entire DICOM file
        (e.g. RTSTRUCT or large series) into memory.
        """
        def _iter_file(path: str):
            with open(path, "rb") as f:
                while chunk := f.read(65536):
                    yield chunk

        with self._client() as client:
            resp = client.post(
                f"{self._base_url}/instances",
                content=_iter_file(file_path),
                headers={"Content-Type": "application/dicom"},
            )
            resp.raise_for_status()
            instance_id: str = resp.json()["ID"]

        logger.info(
            "DICOM file sent to Orthanc",
            extra={"file": Path(file_path).name, "instance_id": instance_id},
        )
        return instance_id
