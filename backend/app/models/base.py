"""Shared column helpers for every ORM model."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

#: Portable primary key type: works identically on SQLite and PostgreSQL.
IdColumn = String(36)


def new_id() -> str:
    return str(uuid4())


def id_pk() -> Mapped[str]:
    return mapped_column(IdColumn, primary_key=True, default=new_id)


def utc_column(*, nullable: bool = False, index: bool = False) -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=nullable, index=index)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
