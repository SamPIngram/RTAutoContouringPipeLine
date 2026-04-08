from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class DatasetFingerprint(Base):
    """nnU-Net-style dataset statistics computed from a training dataset.

    Captures voxel spacing, image sizes, and intensity distributions across
    all NIfTI volumes in the dataset. Used to generate AI guardrails that
    constrain inference inputs to the training data distribution.
    """

    __tablename__ = "dataset_fingerprints"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasets.id"), unique=True, index=True)

    # Aggregate counts
    n_images: Mapped[int] = mapped_column(Integer, default=0)

    # Voxel spacing statistics (mm) — used for pixel-spacing guardrails
    spacing_median: Mapped[list] = mapped_column(JSON)   # [x, y, z]
    spacing_mean: Mapped[list] = mapped_column(JSON)
    spacing_std: Mapped[list] = mapped_column(JSON)
    spacing_p05: Mapped[list] = mapped_column(JSON)
    spacing_p95: Mapped[list] = mapped_column(JSON)

    # Image size statistics (voxels) — used for dimension guardrails
    size_median: Mapped[list] = mapped_column(JSON)      # [x, y, z]
    size_min: Mapped[list] = mapped_column(JSON)
    size_max: Mapped[list] = mapped_column(JSON)

    # Intensity statistics (clipped to p0.5/p99.5)
    intensity_mean: Mapped[float | None] = mapped_column(nullable=True)
    intensity_std: Mapped[float | None] = mapped_column(nullable=True)
    intensity_p05: Mapped[float | None] = mapped_column(nullable=True)
    intensity_p95: Mapped[float | None] = mapped_column(nullable=True)
    intensity_global_min: Mapped[float | None] = mapped_column(nullable=True)
    intensity_global_max: Mapped[float | None] = mapped_column(nullable=True)

    # Detected modalities
    modalities: Mapped[list] = mapped_column(JSON, default=list)

    # Full per-image stats for downstream inspection
    per_image_stats: Mapped[list] = mapped_column(JSON, default=list)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
