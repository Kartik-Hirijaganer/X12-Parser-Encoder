"""Template download endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.services.templates import get_template_bytes

router = APIRouter(tags=["templates"])


@router.get("/templates/{name}")
async def get_template(name: str) -> Response:
    """Download one canonical import template or the template specification."""

    content, media_type = get_template_bytes(name)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
