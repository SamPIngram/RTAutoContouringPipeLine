from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256), unique=True)
    # Raw TOML text of the deployment configuration
    toml_config: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    # Trigger type extracted from TOML: orthanc_new_study, folder_watch, api
    trigger_type: Mapped[str] = mapped_column(String(64))
    # FK to model_registry.id (denormalised for quick lookup)
    model_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
