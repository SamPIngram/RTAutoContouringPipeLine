import logging

from backend.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="backend.tasks.fingerprint.compute_dataset_fingerprint", bind=True)
def compute_dataset_fingerprint(self, dataset_id: int, dataset_dir: str) -> dict:
    """Compute nnU-Net-style fingerprint statistics for a dataset.

    Scans all NIfTI files under dataset_dir/imagesTr, computes voxel spacing,
    image size, and intensity statistics, then stores the result in the
    DatasetFingerprint table.
    """
    from backend.services.preprocessing.fingerprinter import DatasetFingerprinter

    logger.info(
        "Computing dataset fingerprint",
        extra={"dataset_id": dataset_id, "dataset_dir": dataset_dir},
    )

    fingerprinter = DatasetFingerprinter()
    fingerprint = fingerprinter.compute(dataset_dir)
    fingerprint["dataset_id"] = dataset_id

    logger.info(
        "Dataset fingerprint computed",
        extra={"dataset_id": dataset_id, "n_images": fingerprint["n_images"]},
    )
    return fingerprint


@app.task(name="backend.tasks.fingerprint.generate_guardrail_config", bind=True)
def generate_guardrail_config(
    self,
    dataset_id: int,
    fingerprint_data: dict,
    guardrail_name: str,
    modalities: list[str] | None = None,
    output_dir: str = "/data/guardrails",
) -> dict:
    """Generate a healthcare-ai-guardrails YAML from a computed fingerprint.

    Writes the YAML to disk and returns the path + content for DB storage.
    """
    from backend.services.preprocessing.guardrail_generator import GuardrailGenerator

    logger.info(
        "Generating guardrail config",
        extra={"dataset_id": dataset_id, "name": guardrail_name},
    )

    generator = GuardrailGenerator()
    yaml_content = generator.generate(
        fingerprint=fingerprint_data,
        guardrail_name=guardrail_name,
        modalities=modalities,
    )

    yaml_path = generator.save(
        yaml_content=yaml_content,
        output_path=f"{output_dir}/dataset_{dataset_id}_{guardrail_name}.yaml",
    )

    return {
        "dataset_id": dataset_id,
        "guardrail_name": guardrail_name,
        "yaml_content": yaml_content,
        "yaml_path": yaml_path,
    }
