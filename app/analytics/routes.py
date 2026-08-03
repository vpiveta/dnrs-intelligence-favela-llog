from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import BaseOperacional, CasoDNR
from app.core.operational_rules import is_overdue, value_risk_level
from app.core.identity import abbreviate_person

bp = Blueprint("analytics", __name__, url_prefix="/analytics")
CONCLUIDOS = {"RESOLVIDO", "ENCERRADO", "CONCLUIDO"}
RISK_ORDER = ["BAIXO", "MEDIO", "ALTO", "CRITICO"]


def _visible_query():
    query = db.select(CasoDNR)
    if not current_user.can_view_all_bases:
        query = query.where(CasoDNR.base_id == current_user.base_id)
    return query


def _label(value, fallback="Não informado"):
    text = str(value or "").strip()
    return text or fallback


def _top(casos, attr, limit=12):
    grouped = defaultdict(lambda: {"total": 0, "valor": Decimal("0")})
    for c in casos:
        key = _label(getattr(c, attr, None))
        grouped[key]["total"] += 1
        grouped[key]["valor"] += Decimal(c.valor or 0)
    rows = [{"nome": k, **v} for k, v in grouped.items()]
    rows.sort(key=lambda x: (x["total"], x["valor"]), reverse=True)
    return rows[:limit]




def _top_identified(casos, attr, base_labels, consolidated, limit=15):
    grouped = defaultdict(lambda: {"total": 0, "valor": Decimal("0")})
    for c in casos:
        value = _label(getattr(c, attr, None))
        base = base_labels.get(c.base_id, "BASE")
        key = f"{base} · {value}" if consolidated else value
        grouped[key]["total"] += 1
        grouped[key]["valor"] += Decimal(c.valor or 0)
    rows = [{"nome": k, **v} for k, v in grouped.items()]
    rows.sort(key=lambda x: (x["total"], x["valor"]), reverse=True)
    return rows[:limit]


def _multi_series(casos, key_func, bases):
    labels = sorted({str(key_func(c)) for c in casos if key_func(c) is not None})
    datasets = []
    for base in bases:
        counter = Counter(str(key_func(c)) for c in casos if c.base_id == base.id and key_func(c) is not None)
        datasets.append({"label": base.codigo, "data": [counter.get(label, 0) for label in labels]})
    return {"labels": labels, "datasets": datasets}

def _series(casos, key_func):
    counter = Counter()
    for c in casos:
        key = key_func(c)
        if key is not None:
            counter[str(key)] += 1
    return [{"label": k, "value": counter[k]} for k in sorted(counter)]


def _risk_counts(casos):
    counts = Counter(value_risk_level(c.valor) for c in casos)
    return {level: counts.get(level, 0) for level in RISK_ORDER}


def _top_with_others(rows, limit=12):
    if len(rows) <= limit:
        return rows
    kept = rows[:limit]
    rest = rows[limit:]
    kept.append({"nome": "Outros", "total": sum(x["total"] for x in rest), "valor": sum((x["valor"] for x in rest), Decimal("0")), "full": "", "base_id": None})
    return kept


@bp.route("/")
@login_required
def index():
    periodo = request.args.get("periodo", "all")
    base_id = request.args.get("base_id", type=int)
    dias = None
    if periodo != "all":
        try:
            dias = max(7, min(int(periodo), 730))
        except ValueError:
            periodo = "all"
    query = _visible_query()
    if dias:
        inicio = datetime.now(timezone.utc) - timedelta(days=dias)
        query = query.where(CasoDNR.criado_em >= inicio)
    if base_id and (current_user.can_view_all_bases):
        query = query.where(CasoDNR.base_id == base_id)
    casos = db.session.scalars(query.order_by(CasoDNR.criado_em.asc())).all()

    bases = db.session.scalars(
        db.select(BaseOperacional).where(BaseOperacional.ativa.is_(True)).order_by(BaseOperacional.codigo)
    ).all()
    if not current_user.can_view_all_bases:
        bases = [current_user.base]
    total = len(casos)
    resolvidos = sum(c.status in CONCLUIDOS for c in casos)
    risk_counts = _risk_counts(casos)
    overdue_cases = [c for c in casos if is_overdue(c)]

    valor_total = sum((Decimal(c.valor or 0) for c in casos), Decimal("0"))
    cep4_validos = [c.cep4 for c in casos if c.cep4]
    cep4_critico = Counter(cep4_validos).most_common(1)[0] if cep4_validos else ("—", 0)

    consolidated = bool(current_user.can_view_all_bases and not base_id)
    base_labels = {c.base_id: c.base.codigo for c in casos if c.base}
    por_dia = _series(casos, lambda c: c.data_dnr.isoformat() if c.data_dnr else None)
    por_semana = _series(casos, lambda c: f"S{int(c.semana_numero):02d}" if c.semana_numero else None)
    por_mes = _series(casos, lambda c: f"{int(c.ano):04d}-{int(c.mes):02d}" if c.ano and c.mes else None)
    por_horario = _top_identified(casos, "faixa_horaria", base_labels, consolidated, 30)
    # Motorista: BASE · Nome abreviado; nome completo permanece nos detalhes/filtros.
    driver_grouped = defaultdict(lambda: {"total": 0, "valor": Decimal("0"), "full": "", "base_id": None})
    for c in casos:
        full = _label(c.motorista)
        base = base_labels.get(c.base_id, "BASE")
        short = abbreviate_person(full)
        label = f"{base} · {short}" if consolidated else short
        row = driver_grouped[label]
        row["total"] += 1; row["valor"] += Decimal(c.valor or 0); row["full"] = full; row["base_id"] = c.base_id
    motoristas = [{"nome": k, **v} for k,v in driver_grouped.items()]
    motoristas.sort(key=lambda x:(x["total"],x["valor"]), reverse=True); motoristas=_top_with_others(motoristas, 12)
    logins = _top_identified(casos, "login_utilizado", base_labels, consolidated, 20)
    produtos = _top_identified(casos, "produto", base_labels, consolidated, 20)
    categorias = _top_identified(casos, "categoria", base_labels, consolidated, 20)
    cep4_rows = _top_identified(casos, "cep4", base_labels, consolidated, 30)
    status_rows = _top_identified(casos, "status", base_labels, consolidated, 30)

    base_rows = []
    for base in bases:
        items = [c for c in casos if c.base_id == base.id]
        risks = _risk_counts(items)
        conclu = sum(c.status in CONCLUIDOS for c in items)
        base_rows.append({
            "id": base.id,
            "nome": base.codigo,
            "total": len(items),
            "valor": sum((Decimal(c.valor or 0) for c in items), Decimal("0")),
            "resolvidos": conclu,
            "taxa": round(conclu / len(items) * 100) if items else 0,
            "vencidos": sum(is_overdue(c) for c in items),
            **{level.lower(): risks[level] for level in RISK_ORDER},
        })

    week_numbers = sorted({int(c.semana_numero) for c in casos if c.semana_numero})
    current_week = week_numbers[-1] if week_numbers else None
    previous_week = week_numbers[-2] if len(week_numbers) > 1 else None
    comparison = []
    if current_week:
        current_cases = [c for c in casos if c.semana_numero == current_week]
        previous_cases = [c for c in casos if c.semana_numero == previous_week] if previous_week else []
        for base in bases:
            cur_base = [c for c in current_cases if c.base_id == base.id]
            prev_base = [c for c in previous_cases if c.base_id == base.id]
            for label, attr in (("CEP4", "cep4"), ("Motorista", "motorista"), ("Login", "login_utilizado"), ("Produto", "produto")):
                cur = Counter(_label(getattr(c, attr, None)) for c in cur_base)
                prev = Counter(_label(getattr(c, attr, None)) for c in prev_base)
                for name, count in cur.most_common(5):
                    old = prev.get(name, 0)
                    delta = count - old
                    pct = round((delta / old) * 100) if old else (100 if count else 0)
                    comparison.append({"base": base.codigo, "base_id": base.id, "tipo": label, "nome": name, "atual": count, "anterior": old, "delta": delta, "percentual": pct})
        comparison.sort(key=lambda x: (x["delta"], x["atual"]), reverse=True)

    chart_data = {
        "dia": por_dia,
        "semana": por_semana,
        "dia_multi": _multi_series(casos, lambda c: c.data_dnr.isoformat() if c.data_dnr else None, bases) if consolidated else None,
        "semana_multi": _multi_series(casos, lambda c: f"S{int(c.semana_numero):02d}" if c.semana_numero else None, bases) if consolidated else None,
        "mes": por_mes,
        "horario": [{"label": x["nome"], "value": x["total"]} for x in por_horario],
        "motorista": [{"label": x["nome"], "value": x["total"], "filter": x.get("full", ""), "base_id": x.get("base_id")} for x in motoristas],
        "login": [{"label": x["nome"], "value": x["total"], "filter": x["nome"].split(" · ",1)[-1], "base_id": next((c.base_id for c in casos if _label(c.login_utilizado)==x["nome"].split(" · ",1)[-1]), None)} for x in logins],
        "produto": [{"label": x["nome"], "value": x["total"], "filter": x["nome"].split(" · ",1)[-1], "base_id": next((c.base_id for c in casos if _label(c.produto)==x["nome"].split(" · ",1)[-1]), None)} for x in produtos],
        "categoria": [{"label": x["nome"], "value": x["total"]} for x in categorias],
        "cep4": [{"label": x["nome"], "value": x["total"]} for x in cep4_rows if x["nome"] != "Não informado"],
        "base": [{"label": x["nome"], "value": x["total"]} for x in base_rows],
        "base_valor": [{"label": x["nome"], "value": float(x["valor"])} for x in base_rows],
        "status": [{"label": x["nome"], "value": x["total"]} for x in status_rows],
        "risco": [{"label": level.title(), "value": risk_counts[level]} for level in RISK_ORDER],
        "base_risco": {
            "labels": [x["nome"] for x in base_rows],
            "datasets": [
                {"label": "Baixo", "data": [x["baixo"] for x in base_rows]},
                {"label": "Médio", "data": [x["medio"] for x in base_rows]},
                {"label": "Alto", "data": [x["alto"] for x in base_rows]},
                {"label": "Crítico", "data": [x["critico"] for x in base_rows]},
            ],
        },
    }

    return render_template(
        "analytics/index.html", bases=bases, base_id=base_id, periodo=dias,
        total=total, resolvidos=resolvidos, taxa=round(resolvidos / total * 100) if total else 0,
        criticos=risk_counts["CRITICO"], altos=risk_counts["ALTO"], medios=risk_counts["MEDIO"], baixos=risk_counts["BAIXO"],
        vencidos=len(overdue_cases), valor_total=valor_total, cep4_critico=cep4_critico,
        chart_data=chart_data, base_rows=base_rows,
        comparison=comparison[:30], current_week=current_week, previous_week=previous_week,
        consolidated=consolidated,
    )
