import logging

from backend.celery_app import app

logger = logging.getLogger(__name__)


@app.task(
    name="backend.tasks.training.run_training_job",
    bind=True,
    queue="gpu_queue",
)
def run_training_job(
    self,
    dataset_id: int,
    model_name: str,
    framework: str = "nnunet",
    gpu_index: int | None = None,
    extra_config: dict | None = None,
) -> dict:
    """Spawn an ephemeral Docker container to run a training job.

    The container has exclusive access to the specified GPU (or falls back
    to CPU) and is destroyed when the job completes.
    """
    from backend.services.training.docker_runner import DockerRunner

    logger.info(
        "Starting training job",
        extra={"dataset_id": dataset_id, "framework": framework, "gpu_index": gpu_index},
    )

    runner = DockerRunner()
    result = runner.run_training(
        dataset_id=dataset_id,
        model_name=model_name,
        framework=framework,
        gpu_index=gpu_index,
        extra_config=extra_config or {},
    )

    logger.info("Training job complete", extra={"model_path": result.get("model_path")})
    return result
