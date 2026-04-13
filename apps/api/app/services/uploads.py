"""Upload and payload helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TypeVar

from fastapi import HTTPException, Request, UploadFile, status
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.metrics import metric_path_for_request, observe_upload_size

T = TypeVar("T", bound=BaseModel)

_ARCHIVE_EXTENSIONS = {".7z", ".bz2", ".gz", ".rar", ".tar", ".tgz", ".zip"}


@dataclass(slots=True)
class UploadedPayload:
    """In-memory uploaded file payload."""

    filename: str
    extension: str
    content_type: str
    content: bytes


def file_extension(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    return f".{filename.rsplit('.', 1)[-1].lower()}"


async def read_upload_file(
    request: Request,
    upload: UploadFile,
    *,
    allowed_extensions: set[str],
) -> UploadedPayload:
    """Read an upload into memory while enforcing size and type limits."""

    filename = upload.filename or "upload"
    extension = file_extension(filename)
    if extension in _ARCHIVE_EXTENSIONS or extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Unsupported file type.",
                "supported_types": sorted(allowed_extensions),
            },
        )

    content = await upload.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "message": (
                    f"Uploaded payload exceeds the {settings.max_upload_size_bytes} byte limit."
                )
            },
        )

    _attach_upload_audit(
        request,
        content_type=upload.content_type or "application/octet-stream",
        byte_size=len(content),
        file_hash=hashlib.sha256(content).hexdigest(),
    )
    observe_upload_size(
        path=metric_path_for_request(request),
        file_type=extension.lstrip(".") or "unknown",
        byte_size=len(content),
    )

    return UploadedPayload(
        filename=filename,
        extension=extension,
        content_type=upload.content_type or "application/octet-stream",
        content=content,
    )


def decode_text_payload(content: bytes) -> str:
    """Decode uploaded bytes as UTF-8 text with a BOM-tolerant fallback."""

    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"message": "Uploaded file is not valid UTF-8 text."},
    )


def parse_model_json(raw_value: str | None, model_type: type[T]) -> T | None:
    """Parse a JSON string into a Pydantic model."""

    if raw_value is None:
        return None
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid JSON payload in form field.", "field": "config"},
        ) from exc

    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc


def _attach_upload_audit(
    request: Request,
    *,
    content_type: str,
    byte_size: int,
    file_hash: str,
) -> None:
    uploads = getattr(request.state, "upload_audit", [])
    uploads.append(
        {
            "content_type": content_type,
            "byte_size": byte_size,
            "file_hash": file_hash,
        }
    )
    request.state.upload_audit = uploads
