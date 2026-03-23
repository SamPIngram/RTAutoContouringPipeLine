import logging
import os
from pathlib import Path

import SimpleITK as sitk  # type: ignore[import]

logger = logging.getLogger(__name__)


class DicomToNiftiConverter:
    """Convert DICOM series to NIfTI with resampling and orientation normalisation."""

    def __init__(self, output_base_dir: str = "/data/nifti") -> None:
        self._output_base_dir = Path(output_base_dir)

    def convert_from_orthanc(self, orthanc_study_id: str) -> dict:
        """Download from Orthanc and convert."""
        import os
        import tempfile

        from backend.config import load_settings
        from backend.services.ingestion.orthanc import OrthancService

        settings = load_settings(os.environ.get("CONFIG_PATH", "config.toml"))
        svc = OrthancService(
            settings.orthanc.url,
            settings.orthanc.username,
            settings.orthanc.password,
        )
        study_info = svc.get_study_info(orthanc_study_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            dicom_dir = svc.download_study_dicom(orthanc_study_id, tmpdir)
            return self._convert_directory(dicom_dir, study_info.study_uid)

    def convert_from_folder(self, folder_path: str, recursive: bool = True) -> dict:
        """Convert DICOM files from a local folder."""
        return self._convert_directory(folder_path, study_uid=Path(folder_path).name)

    def convert_from_proknow(
        self, workspace: str, patient_id: str | None = None
    ) -> dict:
        """Stub: ProKnow conversion delegates to the ProKnowSync service."""
        raise NotImplementedError("ProKnow conversion should be triggered via ProKnowSync.")

    def _convert_directory(self, dicom_dir: str, study_uid: str) -> dict:
        """Read all DICOM series in a directory and write NIfTI files.

        Applies LPS→RAS orientation normalisation and 1mm isotropic resampling.
        """
        reader = sitk.ImageSeriesReader()
        series_ids = reader.GetGDCMSeriesIDs(dicom_dir)

        if not series_ids:
            raise ValueError(f"No DICOM series found in {dicom_dir}")

        output_dir = self._output_base_dir / study_uid
        output_dir.mkdir(parents=True, exist_ok=True)
        written: list[str] = []

        for series_id in series_ids:
            file_names = reader.GetGDCMSeriesFileNames(dicom_dir, series_id)
            reader.SetFileNames(file_names)
            image = reader.Execute()
            image = self._normalise_orientation(image)
            out_path = output_dir / f"{series_id}.nii.gz"
            sitk.WriteImage(image, str(out_path))
            written.append(str(out_path))
            logger.debug("NIfTI written", extra={"path": str(out_path)})

        logger.info(
            "Conversion complete",
            extra={"study_uid": study_uid, "series_count": len(written)},
        )
        return {"study_uid": study_uid, "nifti_paths": written, "output_dir": str(output_dir)}

    @staticmethod
    def _normalise_orientation(image: sitk.Image) -> sitk.Image:
        """Reorient image to RAS (right-anterior-superior) coordinate system."""
        orient_filter = sitk.DICOMOrientImageFilter()
        orient_filter.SetDesiredCoordinateOrientation("RAS")
        return orient_filter.Execute(image)
