from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import re

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.models import BaseOperacional, CasoDNR, HistoricoCaso
from app.core.operational_rules import critical_context, critical_reasons, is_overdue, sla_date, value_risk_level

bp = Blueprint("cases", __name__, url_prefix="/casos")


def _safe_next(value: str | None) -> str | None:
    """Aceita apenas caminhos internos para evitar redirecionamento externo."""
    text = (value or "").strip()
    if text.startswith("/") and not text.startswith("//"):
        return text
    return None


def _visible_query():
    query = db.select(CasoDNR)
    if not current_user.can_view_all_bases:
        query = query.where(CasoDNR.base_id == current_user.base_id)
    return query


@bp.route("/")
@login_required
def index():
    query = _visible_query()
    busca = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip().upper()
    prioridade = request.args.get("prioridade", "").strip().upper()
    critico = request.args.get("critico", "").strip() == "1"
    vencido = request.args.get("vencido", "").strip() == "1"
    base_id = request.args.get("base_id", type=int)
    cep4 = request.args.get("cep4", "").strip()
    cliente = request.args.get("cliente", "").strip()
    endereco = request.args.get("endereco", "").strip()
    motorista = request.args.get("motorista", "").strip()
    login = request.args.get("login", "").strip()
    produto = request.args.get("produto", "").strip()
    case_ids_raw = request.args.get("case_ids", "").strip()

    if case_ids_raw:
        case_ids = [int(x) for x in case_ids_raw.split(",") if x.strip().isdigit()]
        if case_ids:
            query = query.where(CasoDNR.id.in_(case_ids))
        else:
            query = query.where(CasoDNR.id == -1)
    if busca:
        termo = f"%{busca}%"
        query = query.where(or_(
            CasoDNR.codigo.ilike(termo),
            CasoDNR.tbr.ilike(termo),
            CasoDNR.cliente.ilike(termo),
            CasoDNR.endereco.ilike(termo),
            CasoDNR.motorista.ilike(termo),
            CasoDNR.login_utilizado.ilike(termo),
        ))
    if status:
        query = query.where(CasoDNR.status == status)
    if prioridade and prioridade != "CRITICA":
        query = query.where(CasoDNR.prioridade == prioridade)
    if base_id and (current_user.can_view_all_bases):
        query = query.where(CasoDNR.base_id == base_id)
    if cep4:
        query = query.where(CasoDNR.cep4 == cep4)
    if cliente:
        query = query.where(CasoDNR.cliente == cliente)
    if endereco:
        query = query.where(CasoDNR.endereco == endereco)
    if motorista:
        query = query.where(CasoDNR.motorista == motorista)
    if login:
        query = query.where(CasoDNR.login_utilizado == login)
    if produto:
        query = query.where(CasoDNR.produto == produto)

    casos = db.session.scalars(query.order_by(CasoDNR.criado_em.desc())).all()
    context = critical_context(casos)
    for caso in casos:
        caso.critical_reasons_auto = critical_reasons(caso, context)
        caso.prioridade_automatica = value_risk_level(caso.valor)
        caso.sla_vencimento_auto = sla_date(caso)
        caso.sla_vencido_auto = is_overdue(caso)
    if critico or prioridade == "CRITICA":
        casos = [caso for caso in casos if value_risk_level(caso.valor) == "CRITICO"]
    if vencido:
        casos = [caso for caso in casos if caso.sla_vencido_auto]
    bases = db.session.scalars(db.select(BaseOperacional).where(BaseOperacional.ativa.is_(True)).order_by(BaseOperacional.codigo)).all()
    if not current_user.can_view_all_bases:
        bases = [current_user.base]
    return render_template("cases/index.html", casos=casos, bases=bases)


@bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    bases = db.session.scalars(db.select(BaseOperacional).where(BaseOperacional.ativa.is_(True)).order_by(BaseOperacional.codigo)).all()
    if not current_user.can_view_all_bases:
        bases = [current_user.base]
    if request.method == "POST":
        tbr = request.form.get("tbr", "").strip().upper()
        cliente = request.form.get("cliente", "").strip()
        base_id = request.form.get("base_id", type=int) if (current_user.can_view_all_bases) else current_user.base_id
        if not tbr or not cliente or not base_id:
            flash("TBR, cliente e base são obrigatórios.", "warning")
            return render_template("cases/form.html", bases=bases)

        ultimo = db.session.scalar(db.select(db.func.max(CasoDNR.id))) or 0
        codigo = f"CASO-{date.today().year}-{ultimo + 1:06d}"
        try:
            valor = Decimal(request.form.get("valor", "0").replace(".", "").replace(",", ".") or "0")
        except InvalidOperation:
            valor = Decimal("0")

        caso = CasoDNR(
            codigo=codigo,
            tbr=tbr,
            cliente=cliente,
            endereco=request.form.get("endereco", "").strip(),
            motorista=request.form.get("motorista", "").strip(),
            login_utilizado=request.form.get("login_utilizado", "").strip(),
            login_proprio=(request.form.get("login_proprio") == "SIM") if request.form.get("login_proprio") else None,
            proprietario_login=request.form.get("proprietario_login", "").strip(),
            cep=request.form.get("cep", "").strip(),
            cep4=(re.sub(r"\D", "", request.form.get("cep", "")).zfill(8)[:4] if request.form.get("cep", "").strip() else None),
            produto=request.form.get("produto", "").strip(),
            valor=valor,
            status=request.form.get("status", "PENDENTE").upper(),
            prioridade=request.form.get("prioridade", "MEDIA").upper(),
            data_dnr=datetime.strptime(request.form.get("data_dnr"), "%Y-%m-%d").date() if request.form.get("data_dnr") else None,
            hora_dnr=datetime.strptime(request.form.get("hora_dnr"), "%H:%M").time() if request.form.get("hora_dnr") else None,
            prazo=date.today() + timedelta(days=3),
            base_id=base_id,
        )
        db.session.add(caso)
        db.session.commit()
        flash("Caso criado com sucesso.", "success")
        return redirect(url_for("cases.detalhe", caso_id=caso.id))
    return render_template("cases/form.html", bases=bases)


@bp.route("/<int:caso_id>", methods=["GET", "POST"])
@login_required
def detalhe(caso_id: int):
    back_url = _safe_next(request.values.get("next")) or url_for("cases.index")
    caso = db.session.get(CasoDNR, caso_id)
    if not caso:
        abort(404)
    if not (current_user.can_view_all_bases) and caso.base_id != current_user.base_id:
        abort(403)

    if request.method == "POST":
        status_anterior = caso.status
        caso.status = request.form.get("status", caso.status).upper()
        caso.prioridade = request.form.get("prioridade", caso.prioridade).upper()
        caso.procedimento = request.form.get("procedimento", "").strip()
        caso.responsavel = request.form.get("responsavel", "").strip()
        caso.motorista = request.form.get("motorista", caso.motorista or "").strip()
        caso.login_utilizado = request.form.get("login_utilizado", caso.login_utilizado or "").strip()
        login_proprio = request.form.get("login_proprio", "")
        caso.login_proprio = (login_proprio == "SIM") if login_proprio else None
        caso.proprietario_login = request.form.get("proprietario_login", caso.proprietario_login or "").strip()
        data_dnr = request.form.get("data_dnr", "").strip()
        hora_dnr = request.form.get("hora_dnr", "").strip()
        caso.data_dnr = datetime.strptime(data_dnr, "%Y-%m-%d").date() if data_dnr else caso.data_dnr
        caso.hora_dnr = datetime.strptime(hora_dnr, "%H:%M").time() if hora_dnr else caso.hora_dnr
        historico = HistoricoCaso(
            caso_id=caso.id,
            usuario_id=current_user.id,
            acao="TRATATIVA_ATUALIZADA",
            descricao=caso.procedimento or "Tratativa atualizada sem descrição.",
            status_anterior=status_anterior,
            status_novo=caso.status,
        )
        db.session.add(historico)
        db.session.commit()
        flash("Caso atualizado e registrado na linha do tempo.", "success")
        return redirect(url_for("cases.detalhe", caso_id=caso.id, next=back_url))
    visible = db.session.scalars(_visible_query()).all()
    context = critical_context(visible)
    caso.critical_reasons_auto = critical_reasons(caso, context)
    caso.prioridade_automatica = value_risk_level(caso.valor)
    caso.sla_vencimento_auto = sla_date(caso)
    caso.sla_vencido_auto = is_overdue(caso)
    return render_template("cases/detail.html", caso=caso, back_url=back_url)
