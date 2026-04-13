"""Schemas for health endpoints."""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import ApiModel


class HealthChecks(ApiModel):
    library_import: bool
    parser_smoke: bool
    prometheus_metrics: bool
    profiles_loaded: list[str] = Field(default_factory=list)
    details: list[str] = Field(default_factory=list)


class HealthResponse(ApiModel):
    status: str
    version: str
    checks: HealthChecks
