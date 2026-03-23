import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


def probe_hardware() -> dict:
    """Probe the host for available hardware. Called at application startup."""
    info = {"cuda_available": False, "gpu_count": 0, "gpu_names": []}

    if shutil.which("nvidia-smi") is None:
        logger.info("nvidia-smi not found — GPU support unavailable, using CPU only.")
        return info

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            gpu_names = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
            info["cuda_available"] = len(gpu_names) > 0
            info["gpu_count"] = len(gpu_names)
            info["gpu_names"] = gpu_names
            logger.info("GPU(s) detected", extra={"gpu_count": len(gpu_names), "gpus": gpu_names})
        else:
            logger.warning("nvidia-smi returned non-zero exit code — assuming no GPU.")
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.warning("Could not probe GPU hardware", extra={"error": str(exc)})

    return info


def warn_if_no_gpu(task_name: str) -> None:
    """Log a warning when a GPU task is being executed on CPU."""
    logger.warning(
        "Inference task running on CPU — performance will be degraded.",
        extra={"task": task_name},
    )
