"""Device (UDI-DI) pages, incl. HTMX-managed child rows."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.services import crud
from app.web import form_bool, form_opt, form_str, templates
from eudamed_tool.models import Device, EMDNCode, MarketCountry, TradeName

router = APIRouter(prefix="/devices")


@router.get("")
def list_page(request: Request, basic_udi_id: str = "",
              session: Session = Depends(get_session)):
    # "" comes from the "All Basic UDI-DIs" filter option; ignore bad values
    try:
        filter_id = uuid.UUID(basic_udi_id) if basic_udi_id else None
    except ValueError:
        filter_id = None
    return templates.TemplateResponse(request, "devices/list.html", {
        "rows": crud.list_devices(session, filter_id),
        "basics": crud.list_basic_udis(session),
        "filter_basic_id": filter_id,
    })


def _form_ctx(session: Session, row, errors):
    return {"row": row, "errors": errors, "basics": crud.list_basic_udis(session)}


@router.get("/new")
def new_page(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "devices/form.html",
                                      _form_ctx(session, None, []))


@router.get("/{device_id}")
def edit_page(request: Request, device_id: uuid.UUID,
              session: Session = Depends(get_session)):
    row = crud.get_device(session, device_id)
    return templates.TemplateResponse(request, "devices/form.html",
                                      _form_ctx(session, row, []))


# --- HTMX partials for child-row editing -------------------------------------

@router.get("/partials/trade-name-row")
def trade_name_row(request: Request):
    return templates.TemplateResponse(request, "devices/_trade_name_row.html",
                                      {"language": "EN", "text": ""})


@router.get("/partials/emdn-row")
def emdn_row(request: Request):
    return templates.TemplateResponse(request, "devices/_emdn_row.html",
                                      {"code": "", "description": ""})


@router.get("/partials/market-row")
def market_row(request: Request):
    return templates.TemplateResponse(request, "devices/_market_row.html",
                                      {"country": "DE", "start": "", "end": ""})


# --- form handling ------------------------------------------------------------

async def _model_from_form(request: Request) -> Device:
    form = await request.form()

    def getlist(name: str) -> list[str]:
        return [str(v) for v in form.getlist(name)]

    trade_names = [
        TradeName(language_code=lang, trade_name=text)
        for lang, text in zip(getlist("tn_language"), getlist("tn_text"))
        if text.strip()
    ]
    emdn_codes = [
        EMDNCode(emdn_code=code, emdn_description=(desc.strip() or None))
        for code, desc in zip(getlist("emdn_code"), getlist("emdn_description"))
        if code.strip()
    ]
    market_countries = [
        MarketCountry(
            country_code=c,
            first_market_date=(start or None),
            withdrawal_date=(end or None),
        )
        for c, start, end in zip(getlist("mc_country"), getlist("mc_start"), getlist("mc_end"))
        if c.strip()
    ]
    # sterile/sterilization/latex/reprocessed/single_use, number_of_reuses (-1)
    # and base_quantity (1) are fixed portfolio values -> model defaults apply.
    return Device(
        udi_di=form_str(form, "udi_di"),
        issuing_entity_code=form_str(form, "issuing_entity_code"),
        basic_udi_di=form_str(form, "basic_udi_di"),
        reference_number=form_str(form, "reference_number"),
        device_status=form_str(form, "device_status", "ON_THE_MARKET"),
        intended_purpose=form_opt(form, "intended_purpose"),
        software_version=form_opt(form, "software_version"),
        direct_marking_di=form_opt(form, "direct_marking_di"),
        trade_names=trade_names,
        emdn_codes=emdn_codes,
        production_identifiers=getlist("production_identifiers"),
        market_countries=market_countries,
    )


def _form_errors(exc: ValidationError) -> list[str]:
    return [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]


@router.post("/new")
async def create(request: Request, session: Session = Depends(get_session)):
    try:
        model = await _model_from_form(request)
        crud.save_device(session, model)
    except (ValidationError, ValueError) as exc:
        errors = _form_errors(exc) if isinstance(exc, ValidationError) else [str(exc)]
        return templates.TemplateResponse(request, "devices/form.html",
                                          _form_ctx(session, None, errors))
    except crud.CrudError as exc:
        return templates.TemplateResponse(request, "devices/form.html",
                                          _form_ctx(session, None, [str(exc)]))
    return RedirectResponse("/devices", status_code=303)


@router.post("/{device_id}")
async def update(request: Request, device_id: uuid.UUID,
                 session: Session = Depends(get_session)):
    row = crud.get_device(session, device_id)
    try:
        model = await _model_from_form(request)
        crud.save_device(session, model, device_id)
    except (ValidationError, ValueError) as exc:
        errors = _form_errors(exc) if isinstance(exc, ValidationError) else [str(exc)]
        return templates.TemplateResponse(request, "devices/form.html",
                                          _form_ctx(session, row, errors))
    except crud.CrudError as exc:
        return templates.TemplateResponse(request, "devices/form.html",
                                          _form_ctx(session, row, [str(exc)]))
    return RedirectResponse("/devices", status_code=303)


@router.post("/{device_id}/delete")
def delete(device_id: uuid.UUID, session: Session = Depends(get_session)):
    crud.delete_device(session, device_id)
    return RedirectResponse("/devices", status_code=303)
