import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Docker image used for training jobs (override via config if needed)
DEFAULT_TRAINING_IMAGE = "rtpipeline/training:latest"


class DockerRunner:
    """Spawn ephemeral Docker containers for heavy training jobs.

    Uses the Docker SDK to create a container with:
    - GPU device mapping (if available)
    - Dataset directory mounted read-only
    - Model output directory mounted read-write
    - Auto-removed on exit
    """

    def __init__(self, training_image: str = DEFAULT_TRAINING_IMAGE) -> None:
        self._image = training_image

    def run_training(
        self,
        dataset_id: int,
        model_name: str,
        framework: str = "nnunet",
        gpu_index: int | None = None,
        extra_config: dict | None = None,
    ) -> dict:
        try:
            import docker  # type: ignore[import]
        except ImportError:
            raise RuntimeError("docker package not installed. Run: uv add docker")

        client = docker.from_env()

        dataset_dir = f"/data/datasets/{dataset_id}"
        output_dir = f"/data/models/{model_name}"
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        volumes = {
            dataset_dir: {"bind": "/dataset", "mode": "ro"},
            output_dir: {"bind": "/output", "mode": "rw"},
            "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
        }

        device_requests = []
        if gpu_index is not None:
            device_requests = [
                docker.types.DeviceRequest(
                    device_ids=[str(gpu_index)], capabilities=[["gpu"]]
                )
            ]

        environment = {
            "FRAMEWORK": framework,
            "MODEL_NAME": model_name,
            "DATASET_DIR": "/dataset",
            "OUTPUT_DIR": "/output",
            **(extra_config or {}),
        }

        logger.info(
            "Spawning training container",
            extra={"image": self._image, "gpu_index": gpu_index, "model_name": model_name},
        )

        container = client.containers.run(
            self._image,
            environment=environment,
            volumes=volumes,
            device_requests=device_requests,
            remove=True,
            detach=False,
        )

        logger.info("Training container exited", extra={"model_name": model_name})
        return {"model_path": output_dir, "status": "complete"}
