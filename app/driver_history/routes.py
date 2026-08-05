from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import BaseOperacional, CasoDNR, MotoristaAcompanhamento, TratativaMotorista
from app.core.date_filters import active_filter_params, apply_date_filters, date_filter_context
from app.core.deduplication import deduplicate_cases
from app.core.identity import client_address_key, normalize_text

bp = Blueprint("driver_history", __name__, url_prefix="/historico-motoristas")


def _key(value: str | None) -> str:
    return normalize_text(value or "")


def _scope(query):
    if not current_user.can_view_all_bases:
        query = query.where(CasoDNR.base_id == current_user.base_id)
    return query


def _get_or_create(driver: str, base_id: int) -> MotoristaAcompanhamento:
    key = _key(driver)
    record = db.session.scalar(
        db.select(MotoristaAcompanhamento).where(
            MotoristaAcompanhamento.base_id == base_id,
            MotoristaAcompanhamento.motorista_chave == key,
        )
    )
    if not record:
        record = MotoristaAcompanhamento(motorista=driver, motorista_chave=key, base_id=base_id)
        db.session.add(record)
        db.session.flush()
    elif record.motorista != driver:
        record.motorista = driver
    return record


def _driver_cases(base_id: int, driver_key: str) -> list[CasoDNR]:
    query = _scope(db.select(CasoDNR)).where(CasoDNR.base_id == base_id)
    cases = deduplicate_cases(
        db.session.scalars(
            query.order_by(CasoDNR.ano.desc(), CasoDNR.semana_numero.desc(), CasoDNR.data_dnr.desc())
        ).all()
    )
    return [case for case in cases if _key(case.motorista) == driver_key]


def _score(latest: int, delta: int, total: int) -> tuple[int, str]:
    score = max(0, min(100, 100 - (latest * 8) - (max(delta, 0) * 6) - max(total - 15, 0)))
    if score >= 95:
        return score, "EXCELENTE"
    if score >= 80:
        return score, "BOM"
    if score >= 60:
        return score, "ATENCAO"
    if score >= 40:
        return score, "CRITICO"
    return score, "BLOQUEAR"


@bp.route("/", methods=["GET"])
@login_required
def index():
    base_id = request.args.get("base_id", type=int)
    query = apply_date_filters(_scope(db.select(CasoDNR)))
    if base_id and current_user.can_view_all_bases:
        query = query.where(CasoDNR.base_id == base_id)
    cases = deduplicate_cases(db.session.scalars(query.order_by(CasoDNR.ano.desc(), CasoDNR.semana_numero.desc())).all())

    all_week_keys = sorted({(int(c.ano or datetime.now().year), int(c.semana_numero)) for c in cases if c.semana_numero})
    week_keys = all_week_keys[-5:]
    grouped = defaultdict(lambda: Counter())
    labels = {}
    bases_by_id = {}
    for c in cases:
        if not c.motorista or not c.semana_numero:
            continue
        key = (c.base_id, _key(c.motorista))
        wk = (int(c.ano or datetime.now().year), int(c.semana_numero))
        if wk not in week_keys:
            continue
        grouped[key][wk] += 1
        labels[key] = c.motorista.strip()
        bases_by_id[c.base_id] = c.base

    existing = db.session.scalars(db.select(MotoristaAcompanhamento)).all()
    state_map = {(x.base_id, x.motorista_chave): x for x in existing}
    rows = []
    for identity, counts in grouped.items():
        base_key, driver_key = identity
        values = [counts.get(w, 0) for w in week_keys]
        latest = values[-1] if values else 0
        previous = values[-2] if len(values) > 1 else 0
        delta = latest - previous
        trend = "ALTA" if delta > 0 else "QUEDA" if delta < 0 else "ESTAVEL"
        state = state_map.get(identity)
        threshold = state.limite_bloqueio if state else 8
        score, score_label = _score(latest, delta, sum(values))
        detail_params = active_filter_params()
        detail_params.update({"base_id": base_key, "motorista": labels[identity]})
        rows.append({
            "motorista": labels[identity], "motorista_chave": driver_key,
            "base": bases_by_id.get(base_key), "base_id": base_key,
            "values": values, "total": sum(values), "latest": latest, "previous": previous,
            "delta": delta, "trend": trend, "state": state, "threshold": threshold,
            "suggest_block": latest >= threshold, "score": score, "score_label": score_label,
            "detail_params": detail_params,
        })
    rows.sort(key=lambda r: (r["latest"], r["total"]), reverse=True)

    bases = db.session.scalars(db.select(BaseOperacional).where(BaseOperacional.ativa.is_(True)).order_by(BaseOperacional.codigo)).all()
    if not current_user.can_view_all_bases:
        bases = [current_user.base]
    return render_template(
        "driver_history/index.html", rows=rows, week_keys=week_keys, bases=bases, base_id=base_id,
        active_filters=active_filter_params(), **date_filter_context(),
    )


@bp.get("/detalhe")
@login_required
def detail():
    base_id = request.args.get("base_id", type=int)
    driver = request.args.get("motorista", "").strip()
    driver_key = _key(driver)
    if not base_id or not driver_key:
        flash("Motorista inválido.", "warning")
        return redirect(url_for("driver_history.index", **active_filter_params()))
    if not current_user.can_view_all_bases and base_id != current_user.base_id:
        return redirect(url_for("driver_history.index"))

    cases = _driver_cases(base_id, driver_key)
    if not cases:
        flash("Nenhum DNR localizado para este motorista.", "warning")
        return redirect(url_for("driver_history.index", **active_filter_params()))

    display_name = next((case.motorista.strip() for case in cases if case.motorista), driver)
    base = db.session.get(BaseOperacional, base_id)
    state = db.session.scalar(
        db.select(MotoristaAcompanhamento).where(
            MotoristaAcompanhamento.base_id == base_id,
            MotoristaAcompanhamento.motorista_chave == driver_key,
        )
    )

    all_week_keys = sorted({
        (int(case.ano or datetime.now().year), int(case.semana_numero))
        for case in cases if case.semana_numero
    })
    week_keys = all_week_keys[-5:]
    counts = Counter(
        (int(case.ano or datetime.now().year), int(case.semana_numero))
        for case in cases if case.semana_numero
    )
    values = [counts.get(key, 0) for key in week_keys]
    latest = values[-1] if values else 0
    previous = values[-2] if len(values) > 1 else 0
    delta = latest - previous
    trend = "ALTA" if delta > 0 else "QUEDA" if delta < 0 else "ESTAVEL"
    score, score_label = _score(latest, delta, sum(values))

    total_value = sum((Decimal(case.valor or 0) for case in cases), Decimal("0"))
    categories = Counter((case.categoria or "SEM CATEGORIA").strip() for case in cases)
    clients = Counter(normalize_text(case.cliente or "") for case in cases if case.cliente)
    addresses = Counter(client_address_key(case.cliente, case.endereco) for case in cases if case.endereco)
    recurrent_clients = sum(1 for amount in clients.values() if amount > 1)
    recurrent_addresses = sum(1 for amount in addresses.values() if amount > 1)
    average = round(len(cases) / max(len(all_week_keys), 1), 1)
    best_week = min(((key, counts[key]) for key in all_week_keys), key=lambda item: item[1], default=None)
    worst_week = max(((key, counts[key]) for key in all_week_keys), key=lambda item: item[1], default=None)

    if len(values) >= 2 and values[0] > 0:
        variation = round(((values[-1] - values[0]) / values[0]) * 100)
    else:
        variation = 0
    if trend == "QUEDA":
        insight = f"O motorista reduziu {abs(delta)} DNR em relação à semana anterior."
    elif trend == "ALTA":
        insight = f"O motorista aumentou {delta} DNR na semana atual. Recomenda-se acompanhamento imediato."
    else:
        insight = "O volume de DNR permaneceu estável em relação à semana anterior."

    cases.sort(key=lambda case: (case.data_dnr or datetime.min.date(), case.id), reverse=True)
    return render_template(
        "driver_history/detail.html",
        motorista=display_name, motorista_chave=driver_key, base=base, cases=cases, state=state,
        week_keys=week_keys, values=values, latest=latest, previous=previous, delta=delta, trend=trend,
        score=score, score_label=score_label, total_value=total_value, categories=categories.most_common(5),
        recurrent_clients=recurrent_clients, recurrent_addresses=recurrent_addresses, average=average,
        best_week=best_week, worst_week=worst_week, variation=variation, insight=insight,
        active_filters=active_filter_params(),
    )


@bp.post("/tratativa")
@login_required
def add_treatment():
    driver = request.form.get("motorista", "").strip()
    base_id = request.form.get("base_id", type=int)
    description = request.form.get("descricao", "").strip()
    if not driver or not base_id or not description:
        flash("Informe motorista, base e descrição da tratativa.", "warning")
        return redirect(request.referrer or url_for("driver_history.index"))
    if not current_user.can_view_all_bases and base_id != current_user.base_id:
        return redirect(url_for("driver_history.index"))
    record = _get_or_create(driver, base_id)
    treatment = TratativaMotorista(
        acompanhamento_id=record.id, usuario_id=current_user.id,
        semana_numero=request.form.get("semana_numero", type=int),
        ano=request.form.get("ano", type=int), tipo=request.form.get("tipo", "ORIENTACAO"),
        descricao=description,
    )
    db.session.add(treatment)
    db.session.commit()
    flash("Tratativa registrada no histórico do motorista.", "success")
    return redirect(request.form.get("next") or url_for("driver_history.index"))


@bp.post("/bloqueio")
@login_required
def toggle_block():
    driver = request.form.get("motorista", "").strip()
    base_id = request.form.get("base_id", type=int)
    if not driver or not base_id:
        flash("Motorista inválido.", "danger")
        return redirect(request.referrer or url_for("driver_history.index"))
    if not current_user.can_view_all_bases and base_id != current_user.base_id:
        return redirect(url_for("driver_history.index"))
    record = _get_or_create(driver, base_id)
    record.limite_bloqueio = max(1, request.form.get("limite_bloqueio", type=int) or record.limite_bloqueio or 8)
    action = request.form.get("acao", "bloquear")
    record.bloqueado = action == "bloquear"
    record.motivo_bloqueio = request.form.get("motivo", "").strip() or None
    record.bloqueado_em = datetime.now(timezone.utc) if record.bloqueado else None
    record.bloqueado_por_id = current_user.id if record.bloqueado else None
    db.session.commit()
    flash("Motorista bloqueado para acompanhamento." if record.bloqueado else "Bloqueio removido.", "success")
    return redirect(request.form.get("next") or url_for("driver_history.index"))
