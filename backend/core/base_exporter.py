from abc import ABC, abstractmethod
from pathlib import Path


class BaseExporter(ABC):
    """Base class for pipeline output exporters.

    Subclasses implement specific export destinations:
    - RtStructExporter (DICOM RTSTRUCT via Orthanc)
    - FolderExporter (local/network directory)
    - DownloadExporter (user-initiated download)
    """

    @abstractmethod
    def export(
        self,
        rtstruct_path: str | Path,
        destination_config: dict,
    ) -> dict:
        """Export the RTSTRUCT file to the configured destination.

        Args:
            rtstruct_path: Path to the generated RTSTRUCT DICOM file.
            destination_config: Dict from the [export] section of the deployment TOML.

        Returns:
            Dict with export result metadata (e.g. {"status": "sent", "aet": "CLINICAL_TPS"}).
        """

    @property
    def destination_type(self) -> str:
        raise NotImplementedError
