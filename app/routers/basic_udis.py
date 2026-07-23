"""Basic UDI-DI pages."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.services import crud
from app.web import form_bool, form_str, templates
from eudamed_tool.models import BasicUDI

router = APIRouter(prefix="/basic-udis")

BOOL_FIELDS = [
    "animal_tissues_cells", "human_tissues_cells", "human_product_check",
    "medicinal_product_check", "administering_medicine", "active",
    "implantable", "measuring_function", "reusable",
]


@router.get("")
def list_page(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "basic_udis/list.html",
                                      {"rows": crud.list_basic_udis(session)})


@router.get("/new")
def new_page(request: Request):
    return templates.TemplateResponse(request, "basic_udis/form.html",
                                      {"row": None, "errors": []})


@router.get("/{basic_id}")
def edit_page(request: Request, basic_id: uuid.UUID,
              session: Session = Depends(get_session)):
    row = crud.get_basic_udi(session, basic_id)
    return templates.TemplateResponse(request, "basic_udis/form.html",
                                      {"row": row, "errors": []})


async def _model_from_form(request: Request) -> BasicUDI:
    form = await request.form()
    data = {
        "basic_udi_di": form_str(form, "basic_udi_di"),
        "issuing_entity_code": form_str(form, "issuing_entity_code"),
        "manufacturer_srn": form_str(form, "manufacturer_srn"),
        "risk_class": form_str(form, "risk_class"),
        "model_name": form_str(form, "model_name"),
        "device_type": form_str(form, "device_type", "DEVICE"),
    }
    data.update({f: form_bool(form, f) for f in BOOL_FIELDS})
    return BasicUDI(**data)


def _form_errors(exc: ValidationError) -> list[str]:
    return [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]


@router.post("/new")
async def create(request: Request, session: Session = Depends(get_session)):
    try:
        model = await _model_from_form(request)
        crud.save_basic_udi(session, model)
    except ValidationError as exc:
        return templates.TemplateResponse(request, "basic_udis/form.html",
                                          {"row": None, "errors": _form_errors(exc)})
    except crud.CrudError as exc:
        return templates.TemplateResponse(request, "basic_udis/form.html",
                                          {"row": None, "errors": [str(exc)]})
    return RedirectResponse("/basic-udis", status_code=303)


@router.post("/{basic_id}")
async def update(request: Request, basic_id: uuid.UUID,
                 session: Session = Depends(get_session)):
    row = crud.get_basic_udi(session, basic_id)
    try:
        model = await _model_from_form(request)
        crud.save_basic_udi(session, model, basic_id)
    except ValidationError as exc:
        return templates.TemplateResponse(request, "basic_udis/form.html",
                                          {"row": row, "errors": _form_errors(exc)})
    except crud.CrudError as exc:
        return templates.TemplateResponse(request, "basic_udis/form.html",
                                          {"row": row, "errors": [str(exc)]})
    return RedirectResponse("/basic-udis", status_code=303)


@router.post("/{basic_id}/delete")
def delete(request: Request, basic_id: uuid.UUID,
           session: Session = Depends(get_session)):
    try:
        crud.delete_basic_udi(session, basic_id)
    except crud.CrudError as exc:
        return templates.TemplateResponse(request, "basic_udis/list.html",
                                          {"rows": crud.list_basic_udis(session),
                                           "errors": [str(exc)]})
    return RedirectResponse("/basic-udis", status_code=303)
