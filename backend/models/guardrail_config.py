from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class GuardrailConfig(Base):
    """A healthcare-ai-guardrails YAML configuration derived from a dataset fingerprint.

    Guardrails validate inference inputs against the training data distribution
    before the model runs, catching out-of-distribution studies early.
    """

    __tablename__ = "guardrail_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasets.id"), index=True)
    fingerprint_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("dataset_fingerprints.id"), nullable=True
    )

    # The full YAML text stored in the DB for portability
    yaml_content: Mapped[str] = mapped_column(Text)
    # Path on disk where the YAML is also written (for tooling / CLI use)
    yaml_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Whether this config is the active guardrail for its dataset
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
