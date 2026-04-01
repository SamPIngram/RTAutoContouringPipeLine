import os

from celery import Celery

from backend.config import load_settings

settings = load_settings(os.environ.get("CONFIG_PATH", "config.toml"))

app = Celery(
    "rt_autocontouring",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "backend.tasks.conversion",
        "backend.tasks.training",
        "backend.tasks.inference",
        "backend.tasks.metrics",
        "backend.tasks.fingerprint",
    ],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "backend.tasks.training.run_training_job": {"queue": "gpu_queue"},
        "backend.tasks.inference.run_inference": {"queue": "gpu_queue"},
        "backend.tasks.conversion.convert_dicom_to_nifti": {"queue": "default"},
        "backend.tasks.metrics.compute_geometric_metrics": {"queue": "default"},
        "backend.tasks.fingerprint.compute_dataset_fingerprint": {"queue": "default"},
        "backend.tasks.fingerprint.generate_guardrail_config": {"queue": "default"},
    },
)
