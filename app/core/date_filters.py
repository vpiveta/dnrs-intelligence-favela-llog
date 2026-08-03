from __future__ import annotations

from datetime import datetime
from flask import request
from app.models import CasoDNR


def apply_date_filters(query):
    """Aplica filtros por data exata, intervalo e semana.

    O usuário escolhe se o filtro usa a data de entrega ou a data de abertura do DNR.
    Esses campos são apenas datas operacionais da planilha e não definem o prazo
    de conclusão da análise, que permanece calculado pelo upload do lote.
    Os filtros funcionam junto com o escopo de base já aplicado pela tela.
    """
    source = request.args.get("date_source", "dnr").strip().lower()
    # "dnr" é mantido internamente por compatibilidade; na interface ele representa
    # exclusivamente a Data de entrega.
    column = CasoDNR.data_abertura_dnr if source == "abertura" else CasoDNR.data_dnr
    exact = request.args.get("data", "").strip()
    start = request.args.get("data_inicio", "").strip()
    end = request.args.get("data_fim", "").strip()
    week = request.args.get("semana", type=int)
    year = request.args.get("ano", type=int)

    try:
        if exact:
            query = query.where(column == datetime.strptime(exact, "%Y-%m-%d").date())
        else:
            if start:
                query = query.where(column >= datetime.strptime(start, "%Y-%m-%d").date())
            if end:
                query = query.where(column <= datetime.strptime(end, "%Y-%m-%d").date())
    except ValueError:
        pass

    if week:
        query = query.where(CasoDNR.semana_numero == week)
    if year:
        query = query.where(CasoDNR.ano == year)
    return query


def date_filter_context():
    return {
        "date_source": request.args.get("date_source", "dnr"),
        "data": request.args.get("data", ""),
        "data_inicio": request.args.get("data_inicio", ""),
        "data_fim": request.args.get("data_fim", ""),
        "semana": request.args.get("semana", type=int),
        "ano_filtro": request.args.get("ano", type=int),
    }
