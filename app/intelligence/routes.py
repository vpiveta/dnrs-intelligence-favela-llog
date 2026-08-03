from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import BaseOperacional, CasoDNR
from app.core.operational_rules import value_risk_level

bp = Blueprint("intelligence", __name__, url_prefix="/inteligencia")

CONCLUIDOS = {"RESOLVIDO", "ENCERRADO"}
ABERTOS = {"PENDENTE", "EM_ANALISE", "AGUARDANDO", "AGUARDANDO_RETORNO"}


def _scoped_query():
    query = db.select(CasoDNR)
    if not current_user.can_view_all_bases:
        query = query.where(CasoDNR.base_id == current_user.base_id)
    return query


def _clean(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def _group_rows(casos, attr: str, limit: int = 10):
    grouped: dict[str, list[CasoDNR]] = defaultdict(list)
    labels: dict[str, str] = {}
    for caso in casos:
        label = _clean(getattr(caso, attr, None))
        if not label:
            continue
        key = label.casefold()
        grouped[key].append(caso)
        labels[key] = label
    rows = []
    for key, items in grouped.items():
        total = len(items)
        valor = sum((Decimal(x.valor or 0) for x in items), Decimal("0"))
        abertos = sum(x.status in ABERTOS for x in items)
        rows.append({"nome": labels[key], "total": total, "abertos": abertos, "valor": valor, "reincidente": total > 1})
    rows.sort(key=lambda x: (x["total"], x["valor"]), reverse=True)
    return rows[:limit]



def _driver_login_rows(casos, limit: int = 10):
    grouped = defaultdict(list)
    labels = {}
    for caso in casos:
        motorista = _clean(caso.motorista)
        if not motorista:
            continue
        login = _clean(caso.login_utilizado) or "Login não informado"
        key = (motorista.casefold(), login.casefold())
        grouped[key].append(caso)
        labels[key] = (motorista, login)
    rows = []
    for key, items in grouped.items():
        motorista, login = labels[key]
        rows.append({
            "nome": motorista, "login": login, "total": len(items),
            "abertos": sum(x.status in ABERTOS for x in items),
            "valor": sum((Decimal(x.valor or 0) for x in items), Decimal("0")),
        })
    rows.sort(key=lambda x: (x["total"], x["valor"]), reverse=True)
    return rows[:limit]



def _hour_rows(casos):
    faixas = [
        ("07:30–09:59", 7.5, 10),
        ("10:00–11:59", 10, 12),
        ("12:00–13:59", 12, 14),
        ("14:00–15:59", 14, 16),
        ("16:00–17:59", 16, 18),
        ("18:00 ou mais", 18, 24),
    ]
    rows = []
    total_com_hora = sum(1 for c in casos if c.hora_dnr)
    for label, inicio, fim in faixas:
        items = []
        for caso in casos:
            if not caso.hora_dnr:
                continue
            valor_hora = caso.hora_dnr.hour + caso.hora_dnr.minute / 60
            if inicio <= valor_hora < fim:
                items.append(caso)
        rows.append({
            "nome": label,
            "total": len(items),
            "percentual": round(len(items) / total_com_hora * 100) if total_com_hora else 0,
            "valor": sum((Decimal(c.valor or 0) for c in items), Decimal("0")),
        })
    return rows, total_com_hora


def _procedure_rows(casos):
    grouped: dict[str, list[CasoDNR]] = defaultdict(list)
    labels: dict[str, str] = {}
    for caso in casos:
        proc = _clean(caso.procedimento)
        if not proc:
            continue
        key = proc.casefold()
        grouped[key].append(caso)
        labels[key] = proc
    rows = []
    for key, items in grouped.items():
        total = len(items)
        resolvidos = sum(x.status in CONCLUIDOS for x in items)
        taxa = round(resolvidos / total * 100) if total else 0
        rows.append({"nome": labels[key], "total": total, "resolvidos": resolvidos, "taxa": taxa})
    rows.sort(key=lambda x: (x["taxa"], x["total"]), reverse=True)
    return rows[:12]


def _score(caso: CasoDNR, _client_count: Counter, _address_count: Counter) -> tuple[int, str]:
    nivel = value_risk_level(caso.valor)
    return {"BAIXO": 20, "MEDIO": 45, "ALTO": 75, "CRITICO": 100}[nivel], nivel


@bp.route("/")
@login_required
def index():
    periodo = request.args.get("periodo", "30")
    base_id = request.args.get("base_id", type=int)
    try:
        dias = max(7, min(int(periodo), 365))
    except ValueError:
        dias = 30
    inicio = datetime.now(timezone.utc) - timedelta(days=dias)
    query = _scoped_query().where(CasoDNR.criado_em >= inicio)
    if base_id and (current_user.can_view_all_bases):
        query = query.where(CasoDNR.base_id == base_id)
    casos = db.session.scalars(query.order_by(CasoDNR.criado_em.desc())).all()

    clientes = Counter(_clean(c.cliente).casefold() for c in casos if _clean(c.cliente))
    enderecos = Counter(_clean(c.endereco).casefold() for c in casos if _clean(c.endereco))
    scored = []
    for caso in casos:
        score, nivel = _score(caso, clientes, enderecos)
        scored.append({"caso": caso, "score": score, "nivel": nivel})
    scored.sort(key=lambda x: x["score"], reverse=True)

    total = len(casos)
    resolvidos = sum(c.status in CONCLUIDOS for c in casos)
    taxa_resolucao = round(resolvidos / total * 100) if total else 0
    reinc_clientes = sum(1 for n in clientes.values() if n > 1)
    reinc_enderecos = sum(1 for n in enderecos.values() if n > 1)
    criticos = sum(item["nivel"] == "CRITICO" for item in scored)
    valor_risco = sum((Decimal(item["caso"].valor or 0) for item in scored if item["nivel"] in {"CRITICO", "ALTO"}), Decimal("0"))

    top_clientes = _group_rows(casos, "cliente")
    top_enderecos = _group_rows(casos, "endereco")
    top_motoristas = _driver_login_rows(casos)
    top_produtos = _group_rows(casos, "produto")
    procedimentos = _procedure_rows(casos)
    faixas_horario, total_com_hora = _hour_rows(casos)

    bases = db.session.scalars(db.select(BaseOperacional).where(BaseOperacional.ativa.is_(True)).order_by(BaseOperacional.codigo)).all()
    if not current_user.can_view_all_bases:
        bases = [current_user.base]
    base_stats = []
    for base in bases:
        items = [c for c in casos if c.base_id == base.id]
        if not items and base_id:
            continue
        concluidos = sum(c.status in CONCLUIDOS for c in items)
        base_stats.append({
            "base": base,
            "total": len(items),
            "pendentes": sum(c.status in ABERTOS for c in items),
            "taxa": round(concluidos / len(items) * 100) if items else 0,
            "valor": sum((Decimal(c.valor or 0) for c in items), Decimal("0")),
        })
    base_stats.sort(key=lambda x: x["total"], reverse=True)

    insights = []
    if top_clientes and top_clientes[0]["total"] > 1:
        insights.append({"tipo": "danger", "titulo": "Cliente reincidente", "texto": f"{top_clientes[0]['nome']} possui {top_clientes[0]['total']} ocorrências no período.", "acao": "Priorizar contato e validar histórico."})
    if top_enderecos and top_enderecos[0]["total"] > 1:
        insights.append({"tipo": "warning", "titulo": "Endereço crítico", "texto": f"{top_enderecos[0]['nome']} concentra {top_enderecos[0]['total']} DNR.", "acao": "Revisar roteirização e evidências de entrega."})
    if top_motoristas:
        insights.append({"tipo": "info", "titulo": "Acompanhamento de motorista", "texto": f"{top_motoristas[0]['nome']} aparece em {top_motoristas[0]['total']} casos.", "acao": "Comparar login, horários e regiões atendidas."})
    if procedimentos:
        melhor = procedimentos[0]
        insights.append({"tipo": "success", "titulo": "Procedimento mais efetivo", "texto": f"{melhor['nome']} tem {melhor['taxa']}% de resolução em {melhor['total']} casos.", "acao": "Padronizar quando aplicável."})
    if not insights:
        insights.append({"tipo": "info", "titulo": "Base em formação", "texto": "Ainda não há volume suficiente para recomendações conclusivas.", "acao": "Continue importando e tratando os casos."})

    return render_template(
        "intelligence/index.html",
        casos=scored[:12], total=total, taxa_resolucao=taxa_resolucao,
        reinc_clientes=reinc_clientes, reinc_enderecos=reinc_enderecos,
        criticos=criticos, valor_risco=valor_risco, top_clientes=top_clientes,
        top_enderecos=top_enderecos, top_motoristas=top_motoristas,
        top_produtos=top_produtos, procedimentos=procedimentos,
        bases=bases, base_stats=base_stats, insights=insights,
        periodo=dias, base_id=base_id, faixas_horario=faixas_horario, total_com_hora=total_com_hora,
    )
