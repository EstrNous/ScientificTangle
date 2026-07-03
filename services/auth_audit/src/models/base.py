from datetime import datetime
from sqlalchemy import MetaData
from sqlalchemy.sql import func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

# Строгая конвенция именования ключей для Alembic и PostgreSQL
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Автоматическая генерация имени таблицы из названия класса (UserRole -> userrole)"""
        return cls.__name__.lower()

class TimestampMixin:
    """Миксин для автоматического управления датами создания и обновления"""
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )