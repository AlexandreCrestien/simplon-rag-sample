import uuid as _uuid_mod

from sqlalchemy import MetaData, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator

from rag.config.settings import get_settings

_settings = get_settings()

metadata_obj = MetaData(schema=_settings.postgres_schema)


class PortableUUID(TypeDecorator):
    """UUID stored natively on PostgreSQL, as VARCHAR(36) on other dialects (e.g. SQLite for tests).

    Accepts both uuid.UUID objects and UUID strings as bind parameters.
    Always returns uuid.UUID objects from query results.
    """

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, _uuid_mod.UUID) else _uuid_mod.UUID(str(value))
        return str(value) if isinstance(value, _uuid_mod.UUID) else str(_uuid_mod.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, _uuid_mod.UUID) else _uuid_mod.UUID(str(value))


class Base(DeclarativeBase):
    metadata = metadata_obj
