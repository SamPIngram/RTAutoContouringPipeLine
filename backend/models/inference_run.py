from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class InferenceRun(Base):
    __tablename__ = "inference_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    deployment_id: Mapped[int] = mapped_column(Integer, index=True)
    study_uid: Mapped[str] = mapped_column(String(256), index=True)
    # pending | running | success | failed
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Inference wall-clock time in milliseconds
    inference_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # "gpu" or "cpu"
    hardware_used: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Latency from trigger event to RTSTRUCT export, in milliseconds
    trigger_to_export_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
