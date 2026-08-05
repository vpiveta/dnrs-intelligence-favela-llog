from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
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



def _ensure_history_tables() -> bool:
    """Garante as tabelas do módulo em bancos existentes sem apagar dados."""
    try:
        MotoristaAcompanhamento.__table__.create(bind=db.engine, checkfirst=True)
        TratativaMotorista.__table__.create(bind=db.engine, checkfirst=True)
        return True
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Falha ao preparar tabelas do histórico de motoristas")
        return False


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
    # Bancos que já estavam em produção antes deste módulo podem ainda não ter
    # as tabelas de acompanhamento. A criação é idempotente e preserva dados.
    history_ready = _ensure_history_tables()

    base_id = request.args.get("base_id", type=int)
    query = apply_date_filters(_scope(db.select(CasoDNR)))
    if base_id and current_user.can_view_all_bases:
        query = query.where(CasoDNR.base_id == base_id)

    cases = deduplicate_cases(
        db.session.scalars(
            query.order_by(
                CasoDNR.ano.asc(),
                CasoDNR.semana_numero.asc(),
                CasoDNR.atualizado_em.asc(),
            )
        ).all()
    )

    all_week_keys = sorted({
        (int(c.ano or datetime.now().year), int(c.semana_numero))
        for c in cases
        if c.semana_numero
    })
    week_keys = all_week_keys[-5:]
    grouped = defaultdict(Counter)
    labels: dict[tuple[int, str], str] = {}
    base_codes: dict[int, str] = {}

    for case in cases:
        if not case.motorista or not case.semana_numero:
            continue
        identity = (case.base_id, _key(case.motorista))
        week_key = (int(case.ano or datetime.now().year), int(case.semana_numero))
        if week_key not in week_keys:
            continue
        grouped[identity][week_key] += 1
        labels[identity] = case.motorista.strip()
        base_codes[case.base_id] = case.base.codigo if case.base else "BASE"

    state_map = {}
    if history_ready:
        try:
            state_query = db.select(MotoristaAcompanhamento)
            visible_base_ids = {identity[0] for identity in grouped}
            if visible_base_ids:
                state_query = state_query.where(MotoristaAcompanhamento.base_id.in_(visible_base_ids))
            existing = db.session.scalars(state_query).unique().all()
            state_map = {(item.base_id, item.motorista_chave): item for item in existing}
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Falha ao carregar acompanhamentos de motoristas")
            history_ready = False

    rows = []
    for identity, counts in grouped.items():
        current_base_id, driver_key = identity
        values = [counts.get(week_key, 0) for week_key in week_keys]
        latest = values[-1] if values else 0
        previous = values[-2] if len(values) > 1 else 0
        delta = latest - previous
        trend = "ALTA" if delta > 0 else "QUEDA" if delta < 0 else "ESTAVEL"
        state = state_map.get(identity)
        threshold = int(state.limite_bloqueio if state else 8)
        rows.append({
            "motorista": labels[identity],
            "motorista_chave": driver_key,
            "base_code": base_codes.get(current_base_id, "BASE"),
            "base_id": current_base_id,
            "values": values,
            "total": sum(values),
            "latest": latest,
            "previous": previous,
            "delta": delta,
            "trend": trend,
            "state": state,
            "threshold": threshold,
            "suggest_block": latest >= threshold,
        })
    rows.sort(key=lambda row: (row["latest"], row["total"], row["motorista"]), reverse=True)

    bases_query = db.select(BaseOperacional).where(BaseOperacional.ativa.is_(True)).order_by(BaseOperacional.codigo)
    if not current_user.can_view_all_bases:
        bases_query = bases_query.where(BaseOperacional.id == current_user.base_id)
    bases = db.session.scalars(bases_query).all()

    return render_template(
        "driver_history/index.html",
        rows=rows,
        week_keys=week_keys,
        bases=bases,
        base_id=base_id,
        history_ready=history_ready,
        active_filters=active_filter_params(),
        **date_filter_context(),
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
