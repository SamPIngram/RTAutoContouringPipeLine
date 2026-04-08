import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def probe_hardware() -> dict:
    """Probe the host for available hardware. Called at application startup.

    Detection strategy (in order):
    1. nvidia-smi — most reliable when present.
    2. /dev/nvidia* device files — present when the NVIDIA container runtime
       injects GPU devices even if nvidia-smi is not in the image.
    3. NVIDIA_VISIBLE_DEVICES / CUDA_VISIBLE_DEVICES env vars — set by the
       NVIDIA Container Toolkit; indicates GPUs are assigned to this container.

    Note: python:3.11-slim does not include nvidia-smi. For reliable detection
    inside containers, prefer an NVIDIA base image (e.g. nvidia/cuda:*-runtime)
    or ensure the container runtime sets the NVIDIA_ env vars.
    """
    info: dict = {"cuda_available": False, "gpu_count": 0, "gpu_names": []}

    # --- Strategy 1: nvidia-smi ---
    if shutil.which("nvidia-smi") is not None:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                gpu_names = [
                    line.strip()
                    for line in result.stdout.strip().splitlines()
                    if line.strip()
                ]
                if gpu_names:
                    info.update(
                        cuda_available=True,
                        gpu_count=len(gpu_names),
                        gpu_names=gpu_names,
                    )
                    logger.info(
                        "GPU(s) detected via nvidia-smi",
                        extra={"gpu_count": len(gpu_names), "gpus": gpu_names},
                    )
                    return info
            else:
                logger.warning("nvidia-smi returned non-zero — trying fallback detection.")
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            logger.warning("nvidia-smi probe failed", extra={"error": str(exc)})

    # --- Strategy 2: /dev/nvidia* device files ---
    nvidia_devs = list(Path("/dev").glob("nvidia[0-9]*"))
    if nvidia_devs:
        gpu_count = len(nvidia_devs)
        info.update(cuda_available=True, gpu_count=gpu_count, gpu_names=[])
        logger.info(
            "GPU(s) detected via /dev/nvidia* devices",
            extra={"gpu_count": gpu_count, "devices": [str(d) for d in nvidia_devs]},
        )
        return info

    # --- Strategy 3: NVIDIA Container Toolkit env vars ---
    visible = os.environ.get("NVIDIA_VISIBLE_DEVICES") or os.environ.get("CUDA_VISIBLE_DEVICES")
    if visible and visible.lower() not in ("", "none", "void"):
        # Could be "all", "0,1", "GPU-uuid", etc. — treat as GPU-available.
        gpu_count = len(visible.split(",")) if visible.lower() != "all" else 1
        info.update(cuda_available=True, gpu_count=gpu_count, gpu_names=[])
        logger.info(
            "GPU(s) inferred from NVIDIA env vars",
            extra={"NVIDIA_VISIBLE_DEVICES": visible},
        )
        return info

    logger.info("No GPU detected — using CPU only.")
    return info


def warn_if_no_gpu(task_name: str) -> None:
    """Log a warning when a GPU task is being executed on CPU."""
    logger.warning(
        "Inference task running on CPU — performance will be degraded.",
        extra={"task": task_name},
    )
