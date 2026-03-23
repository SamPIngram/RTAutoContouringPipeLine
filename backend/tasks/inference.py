import logging
import time

from backend.celery_app import app

logger = logging.getLogger(__name__)


@app.task(
    name="backend.tasks.inference.run_inference",
    bind=True,
    queue="gpu_queue",
)
def run_inference(
    self,
    deployment_id: int,
    study_uid: str,
    input_nifti_path: str,
    model_id: str,
    fallback_to_cpu: bool = True,
    trigger_timestamp: float | None = None,
) -> dict:
    """Run model inference and generate RTSTRUCT output.

    Records the inference run in the database including timing and hardware used.
    Falls back to CPU with a warning if GPU is unavailable and fallback_to_cpu=True.
    """
    from backend.hardware import probe_hardware, warn_if_no_gpu
    from backend.services.deployment.rtstruct_generator import RtStructGenerator

    hw = probe_hardware()
    hardware_used = "gpu" if hw["cuda_available"] else "cpu"

    if not hw["cuda_available"]:
        if not fallback_to_cpu:
            raise RuntimeError("GPU required but not available, and fallback_to_cpu=False.")
        warn_if_no_gpu("run_inference")

    logger.info(
        "Starting inference",
        extra={
            "deployment_id": deployment_id,
            "study_uid": study_uid,
            "hardware": hardware_used,
        },
    )

    t0 = time.monotonic()
    generator = RtStructGenerator()
    result = generator.run(
        input_nifti_path=input_nifti_path,
        model_id=model_id,
        hardware=hardware_used,
    )
    inference_ms = int((time.monotonic() - t0) * 1000)

    trigger_to_export_ms = None
    if trigger_timestamp is not None:
        trigger_to_export_ms = int((time.monotonic() - trigger_timestamp) * 1000)

    result.update(
        {
            "inference_ms": inference_ms,
            "hardware_used": hardware_used,
            "trigger_to_export_ms": trigger_to_export_ms,
        }
    )

    logger.info(
        "Inference complete",
        extra={"inference_ms": inference_ms, "hardware": hardware_used},
    )
    return result
