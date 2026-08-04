from __future__ import annotations

from datetime import datetime

from flask import request, session
from flask_login import current_user
from sqlalchemy import distinct

from app.extensions import db
from app.models import CasoDNR

FILTER_SESSION_KEY = "dnr_global_filters"
FILTER_FIELDS = ("base_id", "data", "semana", "ano")


def _coerce_int(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def global_filter_context() -> dict:
    raw = session.get(FILTER_SESSION_KEY, {}) or {}
    return {
        "base_id": _coerce_int(raw.get("base_id")),
        "data": str(raw.get("data") or ""),
        "semana": _coerce_int(raw.get("semana")),
        "ano": _coerce_int(raw.get("ano")),
    }


def sync_global_filters_from_request() -> None:
    """Atualiza o contexto persistente a partir dos filtros presentes na URL.

    ``set_context=1`` substitui todo o contexto (usado por cards semanais e
    formulários). Sem esse marcador, somente os campos explicitamente enviados
    são atualizados, preservando os demais filtros da sessão.
    """
    if request.method != "GET":
        return
    has_filter = any(name in request.args for name in FILTER_FIELDS)
    replace_all = request.args.get("set_context") == "1" or request.args.get("apply_filters") == "1"
    if not has_filter and not replace_all:
        return

    context = {} if replace_all else global_filter_context()
    for name in FILTER_FIELDS:
        if replace_all or name in request.args:
            value = request.args.get(name, "").strip()
            if name in {"base_id", "semana", "ano"}:
                value = _coerce_int(value)
            context[name] = value or None

    # Usuários sem visão global nunca podem persistir outra base.
    if current_user.is_authenticated and not current_user.can_view_all_bases:
        context["base_id"] = current_user.base_id

    session[FILTER_SESSION_KEY] = context
    session.modified = True


def clear_global_filters() -> None:
    session.pop(FILTER_SESSION_KEY, None)
    session.modified = True


def get_filter_value(name: str, *, type_=None, default=None):
    if name in request.args:
        raw = request.args.get(name)
    else:
        raw = global_filter_context().get(name)
    if raw in (None, ""):
        return default
    if type_ is int:
        return _coerce_int(raw)
    if type_ is str:
        return str(raw)
    return raw


def apply_date_filters(query):
    """Aplica o contexto operacional persistente usando a data de entrega."""
    exact = (get_filter_value("data", type_=str, default="") or "").strip()
    week = get_filter_value("semana", type_=int)
    year = get_filter_value("ano", type_=int)

    if exact:
        try:
            query = query.where(CasoDNR.data_dnr == datetime.strptime(exact, "%Y-%m-%d").date())
        except ValueError:
            pass
    if week:
        query = query.where(CasoDNR.semana_numero == week)
    if year:
        query = query.where(CasoDNR.ano == year)
    return query


def selected_filter_base_id() -> int | None:
    if not current_user.can_view_all_bases:
        return current_user.base_id
    return get_filter_value("base_id", type_=int)


def _scope_options(query):
    if not current_user.can_view_all_bases:
        query = query.where(CasoDNR.base_id == current_user.base_id)
    base_id = selected_filter_base_id()
    if base_id and current_user.can_view_all_bases:
        query = query.where(CasoDNR.base_id == base_id)
    return query


def available_filter_options():
    """Retorna somente anos e semanas existentes no escopo global atual."""
    year_query = _scope_options(
        db.select(distinct(CasoDNR.ano)).where(CasoDNR.ano.is_not(None))
    )
    years = sorted(
        (int(value) for value in db.session.scalars(year_query).all() if value),
        reverse=True,
    )

    selected_year = get_filter_value("ano", type_=int)
    week_query = _scope_options(
        db.select(distinct(CasoDNR.semana_numero)).where(CasoDNR.semana_numero.is_not(None))
    )
    if selected_year:
        week_query = week_query.where(CasoDNR.ano == selected_year)
    weeks = sorted(
        (int(value) for value in db.session.scalars(week_query).all() if value)
    )
    return years, weeks


def date_filter_context():
    years, weeks = available_filter_options()
    context = global_filter_context()
    return {
        "base_id": selected_filter_base_id(),
        "data": context.get("data") or "",
        "semana": context.get("semana"),
        "ano_filtro": context.get("ano"),
        "anos_disponiveis": years,
        "semanas_disponiveis": weeks,
    }


def active_filter_params(include_base: bool = True) -> dict:
    """Parâmetros persistentes para links contextuais entre telas."""
    context = global_filter_context()
    params: dict[str, object] = {}
    if include_base:
        base_id = selected_filter_base_id()
        if base_id:
            params["base_id"] = base_id
    if context.get("data"):
        params["data"] = context["data"]
    if context.get("semana"):
        params["semana"] = context["semana"]
    if context.get("ano"):
        params["ano"] = context["ano"]
    return params
