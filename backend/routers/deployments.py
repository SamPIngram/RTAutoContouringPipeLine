import logging
import tomllib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.deployment import Deployment

logger = logging.getLogger(__name__)
router = APIRouter()


class DeploymentCreate(BaseModel):
    name: str
    toml_config: str


class DeploymentResponse(BaseModel):
    id: int
    name: str
    active: bool
    trigger_type: str
    model_id: str | None

    class Config:
        from_attributes = True


def _parse_trigger(toml_text: str) -> tuple[str, str | None]:
    """Extract trigger_type and model_id from TOML config text."""
    try:
        config = tomllib.loads(toml_text)
    except tomllib.TOMLDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid TOML: {e}") from e
    trigger = config.get("workflow", {}).get("trigger", "api")
    model_id = config.get("inference", {}).get("model_id")
    return trigger, model_id


@router.get(
    "/deployments",
    response_model=list[DeploymentResponse],
    summary="List all deployments",
)
async def list_deployments(db: AsyncSession = Depends(get_db)) -> list[Deployment]:
    result = await db.execute(select(Deployment).order_by(Deployment.created_at.desc()))
    return result.scalars().all()


@router.post("/deployments", response_model=DeploymentResponse, summary="Create a deployment")
async def create_deployment(
    body: DeploymentCreate, db: AsyncSession = Depends(get_db)
) -> Deployment:
    trigger, model_id = _parse_trigger(body.toml_config)
    deployment = Deployment(
        name=body.name,
        toml_config=body.toml_config,
        trigger_type=trigger,
        model_id=model_id,
        active=False,
    )
    db.add(deployment)
    await db.commit()
    await db.refresh(deployment)
    logger.info("Deployment created", extra={"deployment_id": deployment.id})
    return deployment


@router.get(
    "/deployments/{deployment_id}",
    response_model=DeploymentResponse,
    summary="Get a deployment",
)
async def get_deployment(
    deployment_id: int, db: AsyncSession = Depends(get_db)
) -> Deployment:
    deployment = await db.get(Deployment, deployment_id)
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment


@router.post(
    "/deployments/{deployment_id}/activate",
    summary="Activate or deactivate a deployment",
)
async def activate_deployment(
    deployment_id: int,
    active: bool = True,
    db: AsyncSession = Depends(get_db),
) -> dict:
    deployment = await db.get(Deployment, deployment_id)
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    deployment.active = active
    await db.commit()
    logger.info(
        "Deployment activation changed",
        extra={"deployment_id": deployment_id, "active": active},
    )
    return {"id": deployment_id, "active": active}


@router.delete("/deployments/{deployment_id}", summary="Delete a deployment")
async def delete_deployment(
    deployment_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    deployment = await db.get(Deployment, deployment_id)
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    await db.delete(deployment)
    await db.commit()
    return {"status": "deleted", "id": deployment_id}
