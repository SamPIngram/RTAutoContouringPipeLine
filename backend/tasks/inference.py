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
    reference_dicom_dir: str,
    fallback_to_cpu: bool = True,
    trigger_timestamp: float | None = None,
    guardrail_yaml: str | None = None,
    guardrail_block_on_failure: bool = False,
) -> dict:
    """Run model inference and generate RTSTRUCT output.

    Optionally validates the input DICOM against a guardrail YAML before
    running the model. If guardrail_block_on_failure=True, the task raises
    on validation failure instead of proceeding.

    Returns a dict with timing metadata and guardrail validation results.
    Persistence of the InferenceRun record is the caller's responsibility.

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
            "guardrail": guardrail_yaml is not None,
        },
    )

    # ── Pre-inference guardrail validation ────────────────────────────────────
    input_guardrail_report: dict | None = None
    if guardrail_yaml:
        from backend.services.inference.guardrail_validator import GuardrailValidator
        validator = GuardrailValidator(guardrail_yaml)
        report = validator.validate_input(
            dicom_dir=reference_dicom_dir,
            block_on_failure=guardrail_block_on_failure,
        )
        input_guardrail_report = report.as_dict()
        logger.info(
            "Input guardrail validation complete",
            extra={"passed": report.passed, "violations": len(report.violations)},
        )

    # ── Model inference ────────────────────────────────────────────────────────
    t0 = time.monotonic()
    generator = RtStructGenerator()
    result = generator.run(
        input_nifti_path=input_nifti_path,
        model_id=model_id,
        hardware=hardware_used,
        reference_dicom_dir=reference_dicom_dir,
    )
    inference_ms = int((time.monotonic() - t0) * 1000)

    # ── Post-inference guardrail validation ───────────────────────────────────
    output_guardrail_report: dict | None = None
    if guardrail_yaml and result.get("rtstruct_path"):
        from backend.services.inference.guardrail_validator import GuardrailValidator
        validator = GuardrailValidator(guardrail_yaml)
        out_report = validator.validate_output(
            rtstruct_path=result["rtstruct_path"],
            block_on_failure=guardrail_block_on_failure,
        )
        output_guardrail_report = out_report.as_dict()

    trigger_to_export_ms = None
    if trigger_timestamp is not None:
        trigger_to_export_ms = int((time.monotonic() - trigger_timestamp) * 1000)

    result.update(
        {
            "inference_ms": inference_ms,
            "hardware_used": hardware_used,
            "trigger_to_export_ms": trigger_to_export_ms,
            "guardrail_input": input_guardrail_report,
            "guardrail_output": output_guardrail_report,
        }
    )

    logger.info(
        "Inference complete",
        extra={"inference_ms": inference_ms, "hardware": hardware_used},
    )
    return result
