"""Dataset fingerprinting — nnU-Net-style statistics over a training cohort.

Computes voxel spacing, image dimensions, and intensity distributions from
all NIfTI volumes in a dataset directory. The resulting fingerprint is used
to generate AI guardrails that constrain inference inputs to remain within
the training data distribution.
"""

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class DatasetFingerprinter:
    """Compute nnU-Net-style statistics from a dataset's NIfTI images."""

    def compute(self, dataset_dir: str) -> dict:
        """Scan all NIfTI files under dataset_dir/imagesTr and compute stats.

        Returns a dict suitable for storing in DatasetFingerprint columns.
        """
        import SimpleITK as sitk  # type: ignore[import]

        images_dir = Path(dataset_dir) / "imagesTr"
        if not images_dir.exists():
            # Fall back to root dir if nnU-Net layout not present
            images_dir = Path(dataset_dir)

        nifti_files = sorted(
            list(images_dir.glob("*.nii.gz")) + list(images_dir.glob("*.nii"))
        )

        if not nifti_files:
            raise ValueError(f"No NIfTI files found in {images_dir}")

        per_image: list[dict] = []
        all_spacings: list[list[float]] = []
        all_sizes: list[list[int]] = []
        all_intensities: list[float] = []

        for nifti_path in nifti_files:
            try:
                image = sitk.ReadImage(str(nifti_path))
                spacing = list(image.GetSpacing())   # (x, y, z) in mm
                size = list(image.GetSize())          # (x, y, z) in voxels

                arr = sitk.GetArrayFromImage(image).astype(np.float32)

                # Robust intensity range (ignore background zeros for MR)
                foreground = arr[arr != 0] if np.any(arr != 0) else arr.ravel()
                p05 = float(np.percentile(foreground, 5))
                p95 = float(np.percentile(foreground, 95))
                p_min = float(np.percentile(foreground, 0.5))
                p_max = float(np.percentile(foreground, 99.5))
                mean = float(np.mean(foreground))
                std = float(np.std(foreground))

                stat = {
                    "filename": nifti_path.name,
                    "spacing": spacing,
                    "size": size,
                    "intensity_mean": mean,
                    "intensity_std": std,
                    "intensity_p05": p05,
                    "intensity_p95": p95,
                    "intensity_min": p_min,
                    "intensity_max": p_max,
                }
                per_image.append(stat)
                all_spacings.append(spacing)
                all_sizes.append(size)
                # Sample intensities for aggregate stats (cap at 100k voxels)
                sample = foreground.ravel()
                if len(sample) > 100_000:
                    rng = np.random.default_rng(seed=42)
                    sample = rng.choice(sample, size=100_000, replace=False)
                all_intensities.extend(sample.tolist())

            except Exception as exc:
                logger.warning(
                    "Could not process NIfTI file",
                    extra={"file": nifti_path.name, "error": str(exc)},
                )

        if not per_image:
            raise ValueError("No NIfTI files could be processed.")

        spacings = np.array(all_spacings)   # (N, 3)
        sizes = np.array(all_sizes)          # (N, 3)
        intensities = np.array(all_intensities, dtype=np.float32)

        def _round(v: float, dp: int = 4) -> float:
            return round(float(v), dp)

        result = {
            "n_images": len(per_image),
            "spacing_median": [_round(v) for v in np.median(spacings, axis=0).tolist()],
            "spacing_mean": [_round(v) for v in np.mean(spacings, axis=0).tolist()],
            "spacing_std": [_round(v) for v in np.std(spacings, axis=0).tolist()],
            "spacing_p05": [_round(v) for v in np.percentile(spacings, 5, axis=0).tolist()],
            "spacing_p95": [_round(v) for v in np.percentile(spacings, 95, axis=0).tolist()],
            "size_median": [int(v) for v in np.median(sizes, axis=0).tolist()],
            "size_min": [int(v) for v in np.min(sizes, axis=0).tolist()],
            "size_max": [int(v) for v in np.max(sizes, axis=0).tolist()],
            "intensity_mean": _round(float(np.mean(intensities))),
            "intensity_std": _round(float(np.std(intensities))),
            "intensity_p05": _round(float(np.percentile(intensities, 5))),
            "intensity_p95": _round(float(np.percentile(intensities, 95))),
            "intensity_global_min": _round(float(np.percentile(intensities, 0.5))),
            "intensity_global_max": _round(float(np.percentile(intensities, 99.5))),
            "modalities": [],   # populated by caller from DICOM metadata
            "per_image_stats": per_image,
        }

        logger.info(
            "Dataset fingerprint computed",
            extra={
                "n_images": result["n_images"],
                "spacing_median": result["spacing_median"],
            },
        )
        return result
