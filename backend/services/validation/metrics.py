import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Compute geometric segmentation metrics: Dice and HD95."""

    def compute(
        self,
        model_id: str,
        dataset_id: int,
        ground_truth_dir: str | None = None,
    ) -> dict:
        """Compute per-structure and mean Dice and HD95.

        Returns a dict with keys: dice, hd95, structure_metrics.
        """
        pred_dir = Path(f"/data/predictions/{model_id}")
        gt_dir = Path(ground_truth_dir) if ground_truth_dir else Path(f"/data/datasets/{dataset_id}/labelsTr")

        if not pred_dir.exists() or not gt_dir.exists():
            raise FileNotFoundError(
                f"Prediction dir {pred_dir} or ground truth dir {gt_dir} not found."
            )

        structure_metrics: dict[str, dict] = {}
        pred_files = sorted(pred_dir.glob("*.nii.gz"))

        for pred_file in pred_files:
            gt_file = gt_dir / pred_file.name
            if not gt_file.exists():
                logger.warning("Ground truth not found", extra={"file": pred_file.name})
                continue

            dice, hd95 = self._compute_pair(str(pred_file), str(gt_file))
            structure_metrics[pred_file.stem] = {"dice": dice, "hd95": hd95}

        if not structure_metrics:
            return {"dice": None, "hd95": None, "structure_metrics": {}}

        mean_dice = float(np.mean([m["dice"] for m in structure_metrics.values()]))
        hd95_values = [m["hd95"] for m in structure_metrics.values() if m["hd95"] is not None]
        mean_hd95: float | None = float(np.mean(hd95_values)) if hd95_values else None

        return {"dice": mean_dice, "hd95": mean_hd95, "structure_metrics": structure_metrics}

    @staticmethod
    def _compute_pair(pred_path: str, gt_path: str) -> tuple[float, float | None]:
        """Compute Dice and HD95 for a single prediction/ground-truth pair."""
        import SimpleITK as sitk  # type: ignore[import]

        pred = sitk.GetArrayFromImage(sitk.ReadImage(pred_path)).astype(bool)
        gt = sitk.GetArrayFromImage(sitk.ReadImage(gt_path)).astype(bool)

        intersection = np.logical_and(pred, gt).sum()
        dice = (2.0 * intersection) / (pred.sum() + gt.sum() + 1e-8)

        hd95 = None
        try:
            from medpy.metric.binary import hd95 as medpy_hd95  # type: ignore[import]
            if pred.any() and gt.any():
                hd95 = float(medpy_hd95(pred, gt))
        except ImportError:
            logger.warning("medpy not available — HD95 will not be computed.")

        return float(dice), hd95
