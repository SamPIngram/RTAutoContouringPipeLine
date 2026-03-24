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

    NOTE: The dataset_dir and output_dir paths (e.g. /data/datasets/<id>) must
    exist on the *Docker host* filesystem, not just inside the backend container.
    When running via docker-compose, ensure the 'pipeline_data' named volume is
    mounted at /data in both the backend container and exposed to the host so that
    sibling training containers can bind-mount the same paths.
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

        # Only mount the data directories — do NOT mount the Docker socket into
        # training containers; they have no need to orchestrate containers and
        # the socket grants root-equivalent access to the host.
        volumes = {
            dataset_dir: {"bind": "/dataset", "mode": "ro"},
            output_dir: {"bind": "/output", "mode": "rw"},
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

        client.containers.run(
            self._image,
            environment=environment,
            volumes=volumes,
            device_requests=device_requests,
            remove=True,
            detach=False,
        )

        logger.info("Training container exited", extra={"model_name": model_name})
        return {"model_path": output_dir, "status": "complete"}
