"""Pydantic models for companion device enrollment."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DeviceEnrollRequest(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    platform: str = Field(default="android", min_length=1, max_length=64)
    capabilities: list[str] = Field(default_factory=list)
    device_id: str | None = Field(default=None, max_length=128)
    meta: dict[str, Any] = Field(default_factory=dict)


class DeviceRecord(BaseModel):
    device_id: str
    label: str
    platform: str
    status: str
    capabilities: list[str] = Field(default_factory=list)
    enrolled_at: str
    revoked_at: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
