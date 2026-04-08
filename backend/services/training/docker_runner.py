import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Docker image used for training jobs (override via config if needed)
DEFAULT_TRAINING_IMAGE = "rtpipeline/training:latest"

# Name of the Docker named volume that holds all pipeline data (/data).
# This must match the volume name declared in docker-compose.yml so that
# training containers can access datasets and write model outputs without
# relying on host-path bind mounts (which are resolved on the Docker daemon
# host and won't match paths inside the backend container).
PIPELINE_DATA_VOLUME = os.environ.get("PIPELINE_DATA_VOLUME", "rtautocontouringpipeline_pipeline_data")


class DockerRunner:
    """Spawn ephemeral Docker containers for heavy training jobs.

    Uses the Docker SDK to create a container with:
    - GPU device mapping (if available)
    - The pipeline_data named volume mounted at /data (read/write)
    - Auto-removed on exit

    NOTE: Training containers access datasets and write model outputs via the
    shared named volume (PIPELINE_DATA_VOLUME → /data).  Do NOT use host-path
    bind mounts for /data/datasets/* or /data/models/*: those paths are inside
    the named volume, not on the host filesystem, and direct bind mounts from
    within the backend container will fail or point to the wrong location.
    """

    def __init__(
        self,
        training_image: str = DEFAULT_TRAINING_IMAGE,
        data_volume: str = PIPELINE_DATA_VOLUME,
    ) -> None:
        self._image = training_image
        self._data_volume = data_volume

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

        dataset_subpath = f"datasets/{dataset_id}"
        output_subpath = f"models/{model_name}"

        # Mount the named volume; the training container accesses data via /data
        # subdirectories set through environment variables.
        volumes = {
            self._data_volume: {"bind": "/data", "mode": "rw"},
        }

        # Ensure the output directory exists inside the volume by creating it
        # via the backend container's own /data mount before spawning the job.
        Path(f"/data/{output_subpath}").mkdir(parents=True, exist_ok=True)

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
            "DATASET_DIR": f"/data/{dataset_subpath}",
            "OUTPUT_DIR": f"/data/{output_subpath}",
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
        return {"model_path": f"/data/{output_subpath}", "status": "complete"}
