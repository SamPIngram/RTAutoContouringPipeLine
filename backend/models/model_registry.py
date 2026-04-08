from datetime import datetime

from sqlalchemy import DateTime, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    version: Mapped[str] = mapped_column(String(64))
    # Framework: nnunet, monai, custom
    framework: Mapped[str] = mapped_column(String(64))
    model_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    trained_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # JSON dict of validation metrics e.g. {"dice": 0.92, "hd95": 3.5}
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    dataset_id: Mapped[int | None] = mapped_column(nullable=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
