import logging
import time
import tomllib

from backend.core.base_trigger import BaseTrigger

logger = logging.getLogger(__name__)


class DeploymentRunner(BaseTrigger):
    """Loads a deployment TOML and routes to the appropriate trigger.

    Lifecycle:
    1. Load and parse the deployment TOML.
    2. listen() starts the trigger (Orthanc webhook listener, folder watcher, or API).
    3. On each trigger event, enqueue inference task and log the run.
    """

    def __init__(self, deployment_id: int, toml_config: str) -> None:
        self._deployment_id = deployment_id
        self._config = tomllib.loads(toml_config)
        self._active = False

    @property
    def trigger_type(self) -> str:
        return self._config.get("workflow", {}).get("trigger", "api")

    def listen(self) -> None:
        self._active = True
        trigger = self.trigger_type
        logger.info(
            "Deployment runner started",
            extra={"deployment_id": self._deployment_id, "trigger": trigger},
        )

        if trigger == "folder_watch":
            from backend.services.ingestion.folder_watcher import FolderWatcher
            watch_path = self._config.get("filtering", {}).get("watch_path", "/data/incoming")
            watcher = FolderWatcher(watch_path)
            watcher.listen()

        elif trigger in ("orthanc_new_study", "api"):
            # These triggers are handled by the FastAPI webhook endpoints.
            # The runner is just registered as active in the DB.
            logger.info("Deployment registered as active — trigger handled by API layer.")
        else:
            raise ValueError(f"Unknown trigger type: {trigger}")

    def stop(self) -> None:
        self._active = False
        logger.info("Deployment runner stopped", extra={"deployment_id": self._deployment_id})

    def handle_study(self, study_uid: str, input_nifti_path: str, trigger_ts: float | None = None) -> str:
        """Dispatch inference for a new study. Returns the Celery task ID."""
        from backend.tasks.inference import run_inference

        inference_cfg = self._config.get("inference", {})
        task = run_inference.delay(
            deployment_id=self._deployment_id,
            study_uid=study_uid,
            input_nifti_path=input_nifti_path,
            model_id=inference_cfg.get("model_id", ""),
            fallback_to_cpu=inference_cfg.get("fallback_to_cpu", True),
            trigger_timestamp=trigger_ts or time.monotonic(),
        )
        logger.info(
            "Inference task dispatched",
            extra={"task_id": task.id, "study_uid": study_uid},
        )
        return task.id
