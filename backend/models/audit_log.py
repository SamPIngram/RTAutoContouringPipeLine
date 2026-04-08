from datetime import datetime

from sqlalchemy import DateTime, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    # e.g. "DICOM_IMPORTED", "DATASET_CREATED", "MODEL_TRAINED", "INFERENCE_COMPLETED"
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    # e.g. "study", "dataset", "model", "deployment"
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    # User login or "system" for automated events
    user_or_system: Mapped[str] = mapped_column(String(128), default="system")
    # Arbitrary JSON payload for event-specific context
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
