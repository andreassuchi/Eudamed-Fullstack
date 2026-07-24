"""Inline UDI-DI / Basic UDI-DI check-digit helper (HTMX fragment)."""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.web import templates
from eudamed_tool.udi import validate_di

router = APIRouter(prefix="/udi")


@router.get("/check")
def check(request: Request, code: str = "", issuing_entity_code: str = "",
          basic: bool = False, field: str = "udi_di"):
    result = validate_di(code, issuing_entity_code, is_basic=basic)
    return templates.TemplateResponse(request, "udi/_check.html", {
        "result": result, "code": code.strip(), "field": field,
    })
