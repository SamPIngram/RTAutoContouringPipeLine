import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class ValidationRequest(BaseModel):
    model_id: int
    dataset_id: int
    ground_truth_dir: str | None = None


class ValidationRunResponse(BaseModel):
    run_id: str
    status: str


class MetricsResponse(BaseModel):
    run_id: str
    status: str
    dice: float | None = None
    hd95: float | None = None
    structure_metrics: dict = {}


@router.post(
    "/validation/run",
    response_model=ValidationRunResponse,
    summary="Start a validation run",
)
async def run_validation(request: ValidationRequest) -> ValidationRunResponse:
    """Enqueue geometric metric computation (Dice, HD95)."""
    from backend.tasks.metrics import compute_geometric_metrics

    task = compute_geometric_metrics.delay(
        model_id=request.model_id,
        dataset_id=request.dataset_id,
        ground_truth_dir=request.ground_truth_dir,
    )
    logger.info("Validation run enqueued", extra={"task_id": task.id})
    return ValidationRunResponse(run_id=task.id, status="queued")


@router.get(
    "/validation/{run_id}/metrics",
    response_model=MetricsResponse,
    summary="Get validation metrics for a run",
)
async def get_metrics(run_id: str) -> MetricsResponse:
    from backend.celery_app import app as celery_app

    result = celery_app.AsyncResult(run_id)
    state = result.state

    if state == "FAILURE":
        raise HTTPException(status_code=500, detail=str(result.result))

    if state != "SUCCESS":
        return MetricsResponse(run_id=run_id, status=state)

    metrics = result.result or {}
    return MetricsResponse(
        run_id=run_id,
        status="success",
        dice=metrics.get("dice"),
        hd95=metrics.get("hd95"),
        structure_metrics=metrics.get("structure_metrics", {}),
    )
