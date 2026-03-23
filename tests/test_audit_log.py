import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.database import Base
from backend.models.audit_log import AuditLog


@pytest_asyncio.fixture
async def db_session():
    """In-memory SQLite session for unit tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


class TestAuditLog:
    async def test_create_audit_log(self, db_session: AsyncSession):
        log = AuditLog(
            event_type="DICOM_IMPORTED",
            entity_type="study",
            entity_id="1.2.3.4",
            user_or_system="system",
            payload={"orthanc_id": "abc123", "modality": "MR"},
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.id is not None
        assert log.event_type == "DICOM_IMPORTED"
        assert log.entity_type == "study"
        assert log.payload["modality"] == "MR"
        assert log.user_or_system == "system"
        assert log.timestamp is not None

    async def test_create_multiple_audit_logs(self, db_session: AsyncSession):
        events = [
            ("DATASET_CREATED", "dataset", "42"),
            ("MODEL_TRAINED", "model", "7"),
            ("INFERENCE_COMPLETED", "inference_run", "99"),
        ]
        for event_type, entity_type, entity_id in events:
            db_session.add(
                AuditLog(
                    event_type=event_type,
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
            )
        await db_session.commit()

        from sqlalchemy import select
        result = await db_session.execute(select(AuditLog))
        logs = result.scalars().all()
        assert len(logs) == 3

    async def test_default_user_or_system(self, db_session: AsyncSession):
        log = AuditLog(event_type="API_CALL", entity_type="deployment")
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)
        assert log.user_or_system == "system"
        assert log.payload == {}
