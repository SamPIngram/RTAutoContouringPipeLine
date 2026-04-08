"""API endpoints for dataset fingerprinting and AI guardrail management."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.dataset import Dataset
from backend.models.dataset_fingerprint import DatasetFingerprint
from backend.models.guardrail_config import GuardrailConfig

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Request / Response models ───────────────────────────────────────────────

class FingerprintResponse(BaseModel):
    id: int
    dataset_id: int
    n_images: int
    spacing_median: list
    spacing_p05: list
    spacing_p95: list
    size_median: list
    size_min: list
    size_max: list
    intensity_mean: float | None
    intensity_std: float | None
    intensity_p05: float | None
    intensity_p95: float | None
    modalities: list
    computed_at: str

    class Config:
        from_attributes = True


class GuardrailGenerateRequest(BaseModel):
    name: str
    modalities: list[str] = Field(default_factory=list)
    block_on_failure: bool = False


class GuardrailResponse(BaseModel):
    id: int
    name: str
    dataset_id: int
    fingerprint_id: int | None
    yaml_path: str | None
    active: bool
    created_at: str

    class Config:
        from_attributes = True


# ─── Fingerprint endpoints ────────────────────────────────────────────────────

@router.post(
    "/datasets/{dataset_id}/fingerprint",
    summary="Compute dataset fingerprint",
    response_model=dict,
)
async def compute_fingerprint(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Enqueue a fingerprinting job for the specified dataset.

    The job scans all NIfTI files in the dataset directory, computes nnU-Net-
    style statistics (spacing, size, intensity), and stores the result.
    """
    dataset = await db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not dataset.dataset_dir:
        raise HTTPException(
            status_code=422,
            detail="Dataset has no dataset_dir. Build the dataset first.",
        )

    from backend.tasks.fingerprint import compute_dataset_fingerprint

    task = compute_dataset_fingerprint.delay(
        dataset_id=dataset_id,
        dataset_dir=dataset.dataset_dir,
    )
    logger.info("Fingerprint task enqueued", extra={"task_id": task.id, "dataset_id": dataset_id})
    return {"status": "queued", "task_id": task.id, "dataset_id": dataset_id}


@router.get(
    "/datasets/{dataset_id}/fingerprint",
    response_model=FingerprintResponse,
    summary="Get stored dataset fingerprint",
)
async def get_fingerprint(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
) -> DatasetFingerprint:
    result = await db.execute(
        select(DatasetFingerprint).where(DatasetFingerprint.dataset_id == dataset_id)
    )
    fp = result.scalar_one_or_none()
    if fp is None:
        raise HTTPException(
            status_code=404,
            detail="Fingerprint not yet computed. POST /datasets/{id}/fingerprint first.",
        )
    return fp


@router.post(
    "/datasets/{dataset_id}/fingerprint/save",
    summary="Save a computed fingerprint result to the database",
    response_model=FingerprintResponse,
)
async def save_fingerprint(
    dataset_id: int,
    fingerprint_data: dict,
    db: AsyncSession = Depends(get_db),
) -> DatasetFingerprint:
    """Persist a fingerprint dict (returned by the Celery task) into the DB."""
    dataset = await db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Upsert: delete existing fingerprint for this dataset if present
    existing = await db.execute(
        select(DatasetFingerprint).where(DatasetFingerprint.dataset_id == dataset_id)
    )
    old = existing.scalar_one_or_none()
    if old:
        await db.delete(old)

    fp = DatasetFingerprint(
        dataset_id=dataset_id,
        n_images=fingerprint_data.get("n_images", 0),
        spacing_median=fingerprint_data.get("spacing_median", []),
        spacing_mean=fingerprint_data.get("spacing_mean", []),
        spacing_std=fingerprint_data.get("spacing_std", []),
        spacing_p05=fingerprint_data.get("spacing_p05", []),
        spacing_p95=fingerprint_data.get("spacing_p95", []),
        size_median=fingerprint_data.get("size_median", []),
        size_min=fingerprint_data.get("size_min", []),
        size_max=fingerprint_data.get("size_max", []),
        intensity_mean=fingerprint_data.get("intensity_mean"),
        intensity_std=fingerprint_data.get("intensity_std"),
        intensity_p05=fingerprint_data.get("intensity_p05"),
        intensity_p95=fingerprint_data.get("intensity_p95"),
        intensity_global_min=fingerprint_data.get("intensity_global_min"),
        intensity_global_max=fingerprint_data.get("intensity_global_max"),
        modalities=fingerprint_data.get("modalities", []),
        per_image_stats=fingerprint_data.get("per_image_stats", []),
    )
    db.add(fp)
    await db.commit()
    await db.refresh(fp)
    logger.info("Fingerprint saved", extra={"dataset_id": dataset_id, "fingerprint_id": fp.id})
    return fp


# ─── Guardrail endpoints ──────────────────────────────────────────────────────

@router.post(
    "/datasets/{dataset_id}/guardrails",
    response_model=GuardrailResponse,
    summary="Generate a guardrail YAML from the dataset fingerprint",
)
async def generate_guardrails(
    dataset_id: int,
    body: GuardrailGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> GuardrailConfig:
    """Generate a healthcare-ai-guardrails YAML from the stored fingerprint.

    The YAML is written to /data/guardrails/ and stored in the DB.
    """
    fp_result = await db.execute(
        select(DatasetFingerprint).where(DatasetFingerprint.dataset_id == dataset_id)
    )
    fp = fp_result.scalar_one_or_none()
    if fp is None:
        raise HTTPException(
            status_code=422,
            detail="No fingerprint found. Run POST /datasets/{id}/fingerprint first.",
        )

    fingerprint_data = {
        "n_images": fp.n_images,
        "spacing_median": fp.spacing_median,
        "spacing_p05": fp.spacing_p05,
        "spacing_p95": fp.spacing_p95,
        "size_median": fp.size_median,
        "size_min": fp.size_min,
        "size_max": fp.size_max,
        "intensity_mean": fp.intensity_mean,
        "intensity_std": fp.intensity_std,
        "intensity_p05": fp.intensity_p05,
        "intensity_p95": fp.intensity_p95,
        "modalities": body.modalities or fp.modalities or ["MR"],
    }

    from backend.services.preprocessing.guardrail_generator import GuardrailGenerator

    generator = GuardrailGenerator()
    yaml_content = generator.generate(
        fingerprint=fingerprint_data,
        guardrail_name=body.name,
        modalities=body.modalities or fp.modalities or ["MR"],
    )
    yaml_path = generator.save(
        yaml_content=yaml_content,
        output_path=f"/data/guardrails/dataset_{dataset_id}_{body.name}.yaml",
    )

    config = GuardrailConfig(
        name=body.name,
        dataset_id=dataset_id,
        fingerprint_id=fp.id,
        yaml_content=yaml_content,
        yaml_path=yaml_path,
        active=True,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    logger.info(
        "Guardrail config created",
        extra={"guardrail_id": config.id, "dataset_id": dataset_id},
    )
    return config


@router.get(
    "/datasets/{dataset_id}/guardrails",
    response_model=list[GuardrailResponse],
    summary="List guardrail configs for a dataset",
)
async def list_guardrails(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[GuardrailConfig]:
    result = await db.execute(
        select(GuardrailConfig)
        .where(GuardrailConfig.dataset_id == dataset_id)
        .order_by(GuardrailConfig.created_at.desc())
    )
    return result.scalars().all()


@router.get(
    "/guardrails/{guardrail_id}",
    response_model=GuardrailResponse,
    summary="Get a guardrail config",
)
async def get_guardrail(
    guardrail_id: int,
    db: AsyncSession = Depends(get_db),
) -> GuardrailConfig:
    config = await db.get(GuardrailConfig, guardrail_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Guardrail config not found")
    return config


@router.get(
    "/guardrails/{guardrail_id}/yaml",
    response_class=PlainTextResponse,
    summary="Download the raw guardrail YAML",
)
async def download_guardrail_yaml(
    guardrail_id: int,
    db: AsyncSession = Depends(get_db),
) -> str:
    config = await db.get(GuardrailConfig, guardrail_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Guardrail config not found")
    return config.yaml_content


@router.delete("/guardrails/{guardrail_id}", summary="Delete a guardrail config")
async def delete_guardrail(
    guardrail_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    config = await db.get(GuardrailConfig, guardrail_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Guardrail config not found")
    await db.delete(config)
    await db.commit()
    return {"status": "deleted", "id": guardrail_id}


# ─── Global guardrail listing (for deployment dropdowns) ─────────────────────

@router.get(
    "/guardrails",
    response_model=list[GuardrailResponse],
    summary="List all guardrail configs",
)
async def list_all_guardrails(db: AsyncSession = Depends(get_db)) -> list[GuardrailConfig]:
    result = await db.execute(
        select(GuardrailConfig).order_by(GuardrailConfig.created_at.desc())
    )
    return result.scalars().all()
