from __future__ import annotations

from datetime import datetime

from flask import request
from flask_login import current_user
from sqlalchemy import distinct

from app.extensions import db
from app.models import CasoDNR


def apply_date_filters(query):
    """Aplica o filtro operacional único do sistema.

    A consulta usa sempre a data de entrega (``data_dnr``). Os controles são:
    dia exato, semana existente no banco e ano. A data de abertura permanece
    disponível no detalhe do caso, mas não interfere nos painéis operacionais.
    """
    exact = request.args.get("data", "").strip()
    week = request.args.get("semana", type=int)
    year = request.args.get("ano", type=int)

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


def _scope_options(query):
    if not current_user.can_view_all_bases:
        query = query.where(CasoDNR.base_id == current_user.base_id)
    base_id = request.args.get("base_id", type=int)
    if base_id and current_user.can_view_all_bases:
        query = query.where(CasoDNR.base_id == base_id)
    return query


def available_filter_options():
    """Retorna somente anos e semanas que existem no banco para o escopo atual."""
    year_query = _scope_options(
        db.select(distinct(CasoDNR.ano)).where(CasoDNR.ano.is_not(None))
    )
    years = sorted(
        (int(value) for value in db.session.scalars(year_query).all() if value),
        reverse=True,
    )

    selected_year = request.args.get("ano", type=int)
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
    return {
        "data": request.args.get("data", ""),
        "semana": request.args.get("semana", type=int),
        "ano_filtro": request.args.get("ano", type=int),
        "anos_disponiveis": years,
        "semanas_disponiveis": weeks,
    }


def active_filter_params(include_base: bool = True) -> dict:
    """Parâmetros operacionais atuais para links contextuais entre telas."""
    params: dict[str, object] = {}
    if include_base:
        base_id = request.args.get("base_id", type=int)
        if base_id:
            params["base_id"] = base_id
    data = request.args.get("data", "").strip()
    semana = request.args.get("semana", type=int)
    ano = request.args.get("ano", type=int)
    if data:
        params["data"] = data
    if semana:
        params["semana"] = semana
    if ano:
        params["ano"] = ano
    return params
