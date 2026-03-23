import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.dataset import Dataset

logger = logging.getLogger(__name__)
router = APIRouter()


class DatasetCreate(BaseModel):
    name: str
    description: str | None = None
    study_ids: list[int] = []


class DatasetResponse(BaseModel):
    id: int
    name: str
    description: str | None
    study_ids: list[int]
    dataset_dir: str | None
    created_by: str

    class Config:
        from_attributes = True


@router.get("/datasets", response_model=list[DatasetResponse], summary="List all datasets")
async def list_datasets(db: AsyncSession = Depends(get_db)) -> list[Dataset]:
    result = await db.execute(select(Dataset).order_by(Dataset.created_at.desc()))
    return result.scalars().all()


@router.post("/datasets", response_model=DatasetResponse, summary="Create a new dataset")
async def create_dataset(
    body: DatasetCreate, db: AsyncSession = Depends(get_db)
) -> Dataset:
    dataset = Dataset(
        name=body.name,
        description=body.description,
        study_ids=body.study_ids,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    logger.info("Dataset created", extra={"dataset_id": dataset.id, "name": dataset.name})
    return dataset


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse, summary="Get a dataset")
async def get_dataset(dataset_id: int, db: AsyncSession = Depends(get_db)) -> Dataset:
    dataset = await db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.delete("/datasets/{dataset_id}", summary="Delete a dataset")
async def delete_dataset(dataset_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    dataset = await db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    await db.delete(dataset)
    await db.commit()
    logger.info("Dataset deleted", extra={"dataset_id": dataset_id})
    return {"status": "deleted", "id": dataset_id}
