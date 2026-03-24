import logging

from backend.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="backend.tasks.metrics.compute_geometric_metrics", bind=True)
def compute_geometric_metrics(
    self,
    model_id: str,
    dataset_id: int,
    ground_truth_dir: str | None = None,
) -> dict:
    """Compute Dice and HD95 metrics for a trained model against a validation set."""
    from backend.services.validation.metrics import MetricsCalculator

    logger.info(
        "Computing geometric metrics",
        extra={"model_id": model_id, "dataset_id": dataset_id},
    )

    calculator = MetricsCalculator()
    metrics = calculator.compute(
        model_id=model_id,
        dataset_id=dataset_id,
        ground_truth_dir=ground_truth_dir,
    )

    logger.info("Metrics computation complete", extra={"metrics": metrics})
    return metrics
