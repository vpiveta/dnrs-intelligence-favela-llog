from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import BaseOperacional, CasoDNR, MotoristaAcompanhamento, TratativaMotorista
from app.core.date_filters import active_filter_params, apply_date_filters, date_filter_context
from app.core.deduplication import deduplicate_cases
from app.core.identity import normalize_text

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
        rows.append({
            "motorista": labels[identity], "motorista_chave": driver_key,
            "base": bases_by_id.get(base_key), "base_id": base_key,
            "values": values, "total": sum(values), "latest": latest, "previous": previous,
            "delta": delta, "trend": trend, "state": state, "threshold": threshold,
            "suggest_block": latest >= threshold,
        })
    rows.sort(key=lambda r: (r["latest"], r["total"]), reverse=True)

    bases = db.session.scalars(db.select(BaseOperacional).where(BaseOperacional.ativa.is_(True)).order_by(BaseOperacional.codigo)).all()
    if not current_user.can_view_all_bases:
        bases = [current_user.base]
    return render_template(
        "driver_history/index.html", rows=rows, week_keys=week_keys, bases=bases, base_id=base_id,
        active_filters=active_filter_params(), **date_filter_context(),
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
