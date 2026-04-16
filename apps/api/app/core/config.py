"""Application settings."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _discover_repo_root() -> Path:
    override = os.getenv("X12_API_REPO_ROOT")
    if override:
        return Path(override).expanduser().resolve()

    search_roots = [Path(__file__).resolve().parent, Path.cwd().resolve()]
    seen: set[Path] = set()
    for root in search_roots:
        for candidate in [root, *root.parents]:
            if candidate in seen:
                continue
            seen.add(candidate)
            if (
                (candidate / "VERSION").exists()
                and (candidate / "apps").exists()
                and (candidate / "packages").exists()
            ):
                return candidate

    return Path.cwd().resolve()


REPO_ROOT = _discover_repo_root()


def _default_frontend_dist_dir() -> Path:
    return REPO_ROOT / "apps" / "web" / "dist"


def _read_version() -> str:
    version_file = REPO_ROOT / "VERSION"
    try:
        return version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"


class AppSettings(BaseSettings):
    """Runtime settings for the API application."""

    app_name: str = "Eligibility Workbench API"
    app_version: str = Field(default_factory=_read_version)
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    frontend_dist_dir: Path = Field(default_factory=_default_frontend_dist_dir)
    serve_frontend: bool = True
    metrics_enabled: bool = True
    metrics_path: str = "/metrics"
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    max_upload_size_bytes: int = 5 * 1024 * 1024
    max_x12_payload_characters: int = 5 * 1024 * 1024
    max_segment_count: int = 20000
    max_elements_per_segment: int = 128

    auth_boundary_enabled: bool = False
    trusted_identity_header: str = "X-Authenticated-User"

    rate_limit_enabled: bool = False
    requests_per_minute: int = 60
    concurrent_upload_limit: int = 5

    model_config = SettingsConfigDict(env_prefix="X12_API_", extra="ignore")

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _parse_cors_allowed_origins(cls, value: object) -> list[str] | object:
        if value is None:
            return []

        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return []
            if normalized.startswith("["):
                try:
                    decoded = json.loads(normalized)
                except json.JSONDecodeError:
                    pass
                else:
                    if isinstance(decoded, list):
                        return [str(item).strip() for item in decoded if str(item).strip()]
            return [item.strip() for item in normalized.split(",") if item.strip()]

        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]

        return value

    @property
    def is_development(self) -> bool:
        return self.environment.lower() in {"dev", "development", "test", "testing"}

    @property
    def frontend_enabled(self) -> bool:
        return self.serve_frontend and (self.frontend_dist_dir / "index.html").exists()


settings = AppSettings()
