from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal

from flask import Blueprint, render_template, request, url_for, redirect
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.models import BaseOperacional, CasoDNR
from app.core.operational_rules import value_risk_level, is_overdue
from app.core.identity import client_address_key, normalize_address
from app.core.date_filters import apply_date_filters, date_filter_context, active_filter_params, selected_filter_base_id, clear_global_filters

bp = Blueprint("dashboard", __name__)


def _scope(query):
    if not current_user.can_view_all_bases:
        query = query.where(CasoDNR.base_id == current_user.base_id)
    return query



@bp.get("/filtros/limpar")
@login_required
def clear_filters():
    clear_global_filters()
    target = request.args.get("next") or request.referrer or url_for("dashboard.index")
    if not str(target).startswith("/"):
        target = url_for("dashboard.index")
    return redirect(target)

@bp.route("/")
@login_required
def index():
    query = apply_date_filters(_scope(db.select(CasoDNR)))
    base_id = selected_filter_base_id()
    if base_id and current_user.can_view_all_bases:
        query = query.where(CasoDNR.base_id == base_id)
    casos = db.session.scalars(query.order_by(CasoDNR.data_dnr.desc(), CasoDNR.criado_em.desc())).all()

    hoje = date.today()
    total = len(casos)
    pendentes_status = {"PENDENTE", "EM_ANALISE", "AGUARDANDO", "AGUARDANDO_RETORNO"}
    concluidos_status = {"RESOLVIDO", "ENCERRADO", "CONCLUIDO"}
    pendentes = sum(c.status in pendentes_status for c in casos)
    criticos = sum(value_risk_level(c.valor) == "CRITICO" for c in casos)
    concluidos = sum(c.status in concluidos_status for c in casos)
    concluidos_hoje = sum(c.status in concluidos_status and c.atualizado_em.date() == hoje for c in casos)
    sem_procedimento = sum(not (c.procedimento or "").strip() for c in casos if c.status not in concluidos_status)
    vencidos = sum(is_overdue(c, hoje) for c in casos)
    aguardando = sum(c.status in {"AGUARDANDO", "AGUARDANDO_RETORNO"} for c in casos)
    valor = sum((Decimal(c.valor or 0) for c in casos), Decimal("0"))
    taxa = round((concluidos / total) * 100) if total else 0

    cliente_counts = Counter(
        (c.base_id, *client_address_key(c.cliente, c.endereco))
        for c in casos
        if client_address_key(c.cliente, c.endereco)[0] and client_address_key(c.cliente, c.endereco)[1]
    )
    endereco_counts = Counter(
        (c.base_id, normalize_address(c.endereco))
        for c in casos if normalize_address(c.endereco)
    )
    clientes_reincidentes = sum(1 for n in cliente_counts.values() if n > 1)
    enderecos_reincidentes = sum(1 for n in endereco_counts.values() if n > 1)

    bases = db.session.scalars(db.select(BaseOperacional).where(BaseOperacional.ativa.is_(True)).order_by(BaseOperacional.codigo)).all()
    if not current_user.can_view_all_bases:
        bases = [current_user.base]
    base_totais = Counter(c.base_id for c in casos)
    maior = max(base_totais.values(), default=1)
    comparativo = []
    for b in bases:
        items = [c for c in casos if c.base_id == b.id]
        total_base = len(items)
        concluidos_base = sum(c.status in concluidos_status for c in items)
        criticos_base = sum(value_risk_level(c.valor) == "CRITICO" for c in items)
        vencidos_base = sum(is_overdue(c, hoje) for c in items)
        valor_base = sum((Decimal(c.valor or 0) for c in items), Decimal("0"))
        comparativo.append({
            "base": b, "total": total_base,
            "percentual": round(total_base / maior * 100) if maior else 0,
            "concluidos": concluidos_base,
            "taxa": round(concluidos_base / total_base * 100) if total_base else 0,
            "criticos": criticos_base, "vencidos": vencidos_base, "valor": valor_base,
        })
    comparativo.sort(key=lambda x: (x["total"], x["valor"]), reverse=True)
    maior_base = comparativo[0] if comparativo else None

    # Cada card abre o Analytics já isolado por base, semana e ano.
    base_by_id = {b.id: b for b in bases}
    weekly_counter = Counter(
        (c.base_id, c.ano or (c.data_dnr.year if c.data_dnr else None), c.semana_numero)
        for c in casos if c.semana_numero
    )
    weekly_cards = []
    for (card_base_id, card_year, week_number), total_week in weekly_counter.items():
        base_obj = base_by_id.get(card_base_id) or db.session.get(BaseOperacional, card_base_id)
        if not base_obj:
            continue
        params = {"base_id": card_base_id, "semana": week_number, "set_context": 1, "data": ""}
        if card_year:
            params["ano"] = card_year
        weekly_cards.append({
            "base": base_obj, "semana": week_number, "ano": card_year,
            "total": total_week, "url": url_for("analytics.index", **params),
        })
    weekly_cards.sort(key=lambda item: (item["ano"] or 0, item["semana"], item["base"].codigo), reverse=True)

    origin = request.full_path.rstrip("?")
    common = active_filter_params()
    common["next"] = origin
    prioridades = [
        {"tipo": "danger", "icone": "!", "titulo": f"{vencidos} casos vencidos", "texto": "Prazo expirado e caso ainda aberto", "url": url_for("cases.index", view="overdue", **common)},
        {"tipo": "danger", "icone": "◆", "titulo": f"{criticos} casos críticos", "texto": "Produtos de R$ 1.000,00 ou mais", "url": url_for("cases.index", view="critical", **common)},
        {"tipo": "warning", "icone": "↻", "titulo": f"{aguardando} aguardando retorno", "texto": "Casos dependentes de resposta ou validação", "url": url_for("cases.index", view="awaiting", **common)},
        {"tipo": "warning", "icone": "□", "titulo": f"{sem_procedimento} sem procedimento", "texto": "Defina a próxima ação operacional", "url": url_for("cases.index", view="no_procedure", **common)},
        {"tipo": "info", "icone": "◎", "titulo": f"{clientes_reincidentes} clientes reincidentes", "texto": "Cliente + endereço com mais de uma ocorrência", "url": url_for("cases.index", view="recurrent_clients", **common)},
        {"tipo": "info", "icone": "⌖", "titulo": f"{enderecos_reincidentes} endereços reincidentes", "texto": "Locais com mais de uma ocorrência", "url": url_for("cases.index", view="recurrent_addresses", **common)},
    ]

    return render_template(
        "dashboard/index.html", total=total, pendentes=pendentes, criticos=criticos,
        concluidos=concluidos, concluidos_hoje=concluidos_hoje, valor=valor,
        taxa=taxa, prioridades=prioridades, casos=casos[:8], bases=bases,
        comparativo=comparativo, base_id=base_id, maior_base=maior_base,
        weekly_cards=weekly_cards, **date_filter_context(),
    )
