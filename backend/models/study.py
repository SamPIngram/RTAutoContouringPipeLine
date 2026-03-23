from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Study(Base):
    __tablename__ = "studies"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(128), index=True)
    study_uid: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    modality: Mapped[str] = mapped_column(String(16))
    series_description: Mapped[str | None] = mapped_column(String(256), nullable=True)
    # Source of import: orthanc_webhook, folder_watch, proknow_sync
    import_source: Mapped[str] = mapped_column(String(64))
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    orthanc_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    nifti_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
