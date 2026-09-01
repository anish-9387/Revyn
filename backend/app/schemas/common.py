"""Shared response primitives. Money always crosses the wire as integer paise."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

ItemT = TypeVar("ItemT")


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class Page(BaseModel, Generic[ItemT]):
    items: list[ItemT]
    total: int
    limit: int
    offset: int


class Acknowledgement(BaseModel):
    ok: bool = True
    message: str = ""
    detail: dict[str, Any] = {}
