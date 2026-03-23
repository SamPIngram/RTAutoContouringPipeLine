import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class DatasetBuilder:
    """Assembles a training dataset from Study NIfTI files."""

    def __init__(self, data_base_dir: str = "/data") -> None:
        self._data_base_dir = Path(data_base_dir)

    def build(self, dataset_id: int, study_ids: list[int], nifti_base: str = "/data/nifti") -> str:
        """Copy NIfTI files for the given study IDs into a dataset directory.

        Returns the path to the created dataset directory.
        """
        dataset_dir = self._data_base_dir / "datasets" / str(dataset_id)
        images_dir = dataset_dir / "imagesTr"
        images_dir.mkdir(parents=True, exist_ok=True)

        nifti_root = Path(nifti_base)
        copied = 0

        for study_id in study_ids:
            study_nifti_dirs = list(nifti_root.glob(f"*{study_id}*"))
            for study_dir in study_nifti_dirs:
                for nifti_file in study_dir.glob("*.nii.gz"):
                    dest = images_dir / nifti_file.name
                    shutil.copy2(nifti_file, dest)
                    copied += 1

        logger.info(
            "Dataset built",
            extra={"dataset_id": dataset_id, "files_copied": copied, "path": str(dataset_dir)},
        )
        return str(dataset_dir)
