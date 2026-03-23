import logging
import subprocess
from pathlib import Path

from backend.core.base_model_runner import BaseModelRunner

logger = logging.getLogger(__name__)


class NnUNetRunner(BaseModelRunner):
    """Run nnU-Net v2 training and inference via its CLI."""

    @property
    def framework_name(self) -> str:
        return "nnunet"

    def predict(
        self,
        input_dir: str | Path,
        output_dir: str | Path,
        config: dict,
    ) -> Path:
        """Run nnUNetv2_predict for the specified model.

        Expected config keys:
          - model_id: nnU-Net dataset/trainer identifier (e.g. "Dataset001_Prostate")
          - configuration: nnU-Net configuration name (e.g. "3d_fullres")
          - fold: fold index or "all"
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        model_id = config["model_id"]
        configuration = config.get("configuration", "3d_fullres")
        fold = str(config.get("fold", "all"))

        cmd = [
            "nnUNetv2_predict",
            "-i", str(input_dir),
            "-o", str(output_dir),
            "-d", model_id,
            "-c", configuration,
            "-f", fold,
            "--save_probabilities",
        ]

        logger.info("Running nnU-Net prediction", extra={"cmd": " ".join(cmd)})
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"nnUNetv2_predict failed:\n{result.stderr}")

        logger.info("nnU-Net prediction complete", extra={"output_dir": str(output_dir)})
        return output_dir

    def train(
        self,
        dataset_dir: str | Path,
        model_name: str,
        configuration: str = "3d_fullres",
        fold: int = 0,
        gpu_index: int | None = None,
    ) -> Path:
        """Run nnUNetv2_train.

        Returns the path to the trained model results directory.
        """
        dataset_dir = Path(dataset_dir)
        env_vars = {}
        if gpu_index is not None:
            env_vars["CUDA_VISIBLE_DEVICES"] = str(gpu_index)

        cmd = [
            "nnUNetv2_train",
            model_name,
            configuration,
            str(fold),
        ]

        import os
        env = {**os.environ, **env_vars}
        logger.info("Running nnU-Net training", extra={"cmd": " ".join(cmd)})
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)

        if result.returncode != 0:
            raise RuntimeError(f"nnUNetv2_train failed:\n{result.stderr}")

        return dataset_dir
