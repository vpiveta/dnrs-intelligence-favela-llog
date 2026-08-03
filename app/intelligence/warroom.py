from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import BaseOperacional, CasoDNR
from app.core.operational_rules import critical_context, is_overdue, sla_date, value_risk_level, value_risk_reason

bp = Blueprint("warroom", __name__, url_prefix="/sala-de-guerra")

CONCLUIDOS = {"RESOLVIDO", "ENCERRADO"}
ABERTOS = {"PENDENTE", "EM_ANALISE", "AGUARDANDO", "AGUARDANDO_RETORNO"}


def _clean(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def _scope(query):
    if not current_user.can_view_all_bases:
        query = query.where(CasoDNR.base_id == current_user.base_id)
    return query


def _case_date(caso: CasoDNR) -> date:
    if caso.data_dnr:
        return caso.data_dnr
    criado = caso.criado_em
    return criado.date() if criado else date.today()


def _risk(caso: CasoDNR, _context: dict[str, object], cliente_counts: Counter, endereco_counts: Counter) -> tuple[int, str, list[str]]:
    """Classificação automática baseada no valor do produto.

    Recorrências de cliente e endereço continuam aparecendo nas análises, mas
    não alteram a faixa oficial de risco financeiro do caso.
    """
    nivel = value_risk_level(caso.valor)
    motivos = [value_risk_reason(caso.valor)]
    score_by_level = {"BAIXO": 20, "MEDIO": 45, "ALTO": 75, "CRITICO": 100}
    score = score_by_level[nivel]

    if is_overdue(caso):
        motivos.append(f"prazo de 3 dias vencido em {sla_date(caso).strftime('%d/%m/%Y')}")
    if not _clean(caso.procedimento) and caso.status not in CONCLUIDOS:
        motivos.append("sem procedimento")

    cliente_key = _clean(caso.cliente).casefold()
    if cliente_key and cliente_counts[cliente_key] > 1:
        motivos.append(f"cliente com {cliente_counts[cliente_key]} ocorrências")
    endereco_key = _clean(caso.endereco).casefold()
    if endereco_key and endereco_counts[endereco_key] > 1:
        motivos.append(f"endereço com {endereco_counts[endereco_key]} ocorrências")
    return score, nivel, motivos

def _trend_rows(casos: list[CasoDNR], attr: str, inicio_atual: date, inicio_anterior: date, fim_anterior: date, limit: int = 8):
    atual: Counter = Counter()
    anterior: Counter = Counter()
    labels: dict[str, str] = {}
    for caso in casos:
        label = _clean(getattr(caso, attr, None))
        if not label:
            continue
        key = label.casefold()
        labels[key] = label
        dia = _case_date(caso)
        if dia >= inicio_atual:
            atual[key] += 1
        elif inicio_anterior <= dia <= fim_anterior:
            anterior[key] += 1
    rows = []
    for key in set(atual) | set(anterior):
        a = atual[key]
        b = anterior[key]
        if a == 0 and b == 0:
            continue
        variacao = 100 if b == 0 and a > 0 else round(((a - b) / b) * 100) if b else 0
        rows.append({"nome": labels.get(key, key), "atual": a, "anterior": b, "variacao": variacao})
    rows.sort(key=lambda item: (item["variacao"], item["atual"]), reverse=True)
    return rows[:limit]


def _procedure_rows(casos: list[CasoDNR]):
    grouped: dict[str, list[CasoDNR]] = defaultdict(list)
    labels: dict[str, str] = {}
    for caso in casos:
        proc = _clean(caso.procedimento)
        if not proc:
            continue
        primeira = proc.splitlines()[0][:90]
        key = primeira.casefold()
        grouped[key].append(caso)
        labels[key] = primeira
    rows = []
    for key, items in grouped.items():
        total = len(items)
        resolvidos = sum(c.status in CONCLUIDOS for c in items)
        rows.append({
            "nome": labels[key], "total": total, "resolvidos": resolvidos,
            "taxa": round(resolvidos / total * 100) if total else 0,
        })
    rows.sort(key=lambda x: (x["taxa"], x["total"]), reverse=True)
    return rows[:10]


@bp.route("/")
@login_required
def index():
    base_id = request.args.get("base_id", type=int)
    periodo = request.args.get("periodo", "30")
    try:
        dias = max(14, min(int(periodo), 365))
    except ValueError:
        dias = 30

    inicio = date.today() - timedelta(days=dias - 1)
    query = _scope(db.select(CasoDNR))
    if base_id and (current_user.can_view_all_bases):
        query = query.where(CasoDNR.base_id == base_id)
    casos = db.session.scalars(query.order_by(CasoDNR.criado_em.desc())).all()
    casos = [c for c in casos if _case_date(c) >= inicio]

    clientes = Counter(_clean(c.cliente).casefold() for c in casos if _clean(c.cliente))
    enderecos = Counter(_clean(c.endereco).casefold() for c in casos if _clean(c.endereco))
    critical = critical_context(casos)

    scored = []
    for caso in casos:
        score, nivel, motivos = _risk(caso, critical, clientes, enderecos)
        scored.append({"caso": caso, "score": score, "nivel": nivel, "motivos": motivos})
    scored.sort(key=lambda x: (x["score"], Decimal(x["caso"].valor or 0)), reverse=True)

    hoje = date.today()
    vencidos = [x for x in scored if is_overdue(x["caso"], hoje)]
    sem_procedimento = [x for x in scored if not _clean(x["caso"].procedimento) and x["caso"].status not in CONCLUIDOS]
    aguardando = [x for x in scored if x["caso"].status in {"AGUARDANDO", "AGUARDANDO_RETORNO"}]
    criticos = [x for x in scored if x["nivel"] == "CRITICO"]
    altos = [x for x in scored if x["nivel"] == "ALTO"]
    medios = [x for x in scored if x["nivel"] == "MEDIO"]
    baixos = [x for x in scored if x["nivel"] == "BAIXO"]
    valor_risco = sum((Decimal(x["caso"].valor or 0) for x in scored if x["nivel"] in {"CRITICO", "ALTO"}), Decimal("0"))

    inicio_atual = hoje - timedelta(days=6)
    fim_anterior = inicio_atual - timedelta(days=1)
    inicio_anterior = fim_anterior - timedelta(days=6)

    tendencias_endereco = _trend_rows(casos, "endereco", inicio_atual, inicio_anterior, fim_anterior)
    tendencias_motorista = _trend_rows(casos, "motorista", inicio_atual, inicio_anterior, fim_anterior)
    tendencias_login = _trend_rows(casos, "login_utilizado", inicio_atual, inicio_anterior, fim_anterior)
    tendencias_produto = _trend_rows(casos, "produto", inicio_atual, inicio_anterior, fim_anterior)
    procedimentos = _procedure_rows(casos)

    alertas = []
    if criticos:
        alertas.append({"tipo": "danger", "titulo": f"{len(criticos)} casos críticos", "texto": "Produtos de R$ 1.000,00 ou mais, conforme a faixa automática de risco financeiro.", "acao": "Abrir casos prioritários", "url": "cases.index", "params": "critico=1"})
    if vencidos:
        alertas.append({"tipo": "danger", "titulo": f"{len(vencidos)} casos com SLA vencido", "texto": "Existem tratativas abertas há mais de 3 dias após o upload da planilha.", "acao": "Revisar responsáveis", "url": "cases.index", "params": "vencido=1"})
    if sem_procedimento:
        alertas.append({"tipo": "warning", "titulo": f"{len(sem_procedimento)} casos sem procedimento", "texto": "Esses casos ainda não possuem ação operacional registrada.", "acao": "Registrar ações", "url": "cases.index", "params": ""})
    if tendencias_endereco and tendencias_endereco[0]["variacao"] > 0:
        top = tendencias_endereco[0]
        alertas.append({"tipo": "warning", "titulo": "Endereço em crescimento", "texto": f"{top['nome']} variou {top['variacao']:+d}% nesta semana ({top['atual']} ocorrências).", "acao": "Abrir no mapa", "url": "geo.index", "params": f"q={top['nome']}"})
    if tendencias_login and tendencias_login[0]["variacao"] > 0:
        top = tendencias_login[0]
        alertas.append({"tipo": "info", "titulo": "Login acima da semana anterior", "texto": f"{top['nome']} variou {top['variacao']:+d}% e aparece em {top['atual']} casos.", "acao": "Analisar login", "url": "geo.index", "params": f"login={top['nome']}"})
    if procedimentos:
        melhor = procedimentos[0]
        alertas.append({"tipo": "success", "titulo": "Procedimento com melhor resultado", "texto": f"{melhor['nome']} apresenta {melhor['taxa']}% de resolução em {melhor['total']} casos.", "acao": "Ver inteligência", "url": "intelligence.index", "params": ""})
    if not alertas:
        alertas.append({"tipo": "success", "titulo": "Nenhum alerta crítico", "texto": "A operação não possui sinais críticos suficientes no período selecionado.", "acao": "Ver casos", "url": "cases.index", "params": ""})

    bases = db.session.scalars(db.select(BaseOperacional).where(BaseOperacional.ativa.is_(True)).order_by(BaseOperacional.codigo)).all()
    if not current_user.can_view_all_bases:
        bases = [current_user.base]
    base_rows = []
    for base in bases:
        items = [c for c in casos if c.base_id == base.id]
        if not items and base_id:
            continue
        abertos = sum(c.status in ABERTOS for c in items)
        concluidos = sum(c.status in CONCLUIDOS for c in items)
        base_rows.append({
            "base": base, "total": len(items), "abertos": abertos,
            "taxa": round(concluidos / len(items) * 100) if items else 0,
            "valor": sum((Decimal(c.valor or 0) for c in items), Decimal("0")),
        })
    base_rows.sort(key=lambda x: (x["abertos"], x["total"]), reverse=True)

    return render_template(
        "intelligence/warroom.html",
        total=len(casos), criticos=len(criticos), altos=len(altos), medios=len(medios), baixos=len(baixos), vencidos=len(vencidos),
        sem_procedimento=len(sem_procedimento), aguardando=len(aguardando),
        valor_risco=valor_risco, alertas=alertas, casos_prioritarios=scored[:12],
        tendencias_endereco=tendencias_endereco, tendencias_motorista=tendencias_motorista,
        tendencias_login=tendencias_login, tendencias_produto=tendencias_produto,
        procedimentos=procedimentos, bases=bases, base_rows=base_rows,
        periodo=dias, base_id=base_id, critical_context=critical,
    )
