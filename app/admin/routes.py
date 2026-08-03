from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from app.core.decorators import admin_required
from app.extensions import db
from app.models import BaseOperacional, User
from app.core.platform import platform_health

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/bases", methods=["GET", "POST"])
@login_required
@admin_required
def bases():
    if request.method == "POST":
        codigo = request.form.get("codigo", "").strip().upper()
        nome = request.form.get("nome", "").strip()
        cidade = request.form.get("cidade", "").strip()
        if not codigo or not nome:
            flash("Código e nome são obrigatórios.", "warning")
        elif db.session.scalar(db.select(BaseOperacional).where(BaseOperacional.codigo == codigo)):
            flash("Já existe uma base com esse código.", "warning")
        else:
            db.session.add(BaseOperacional(codigo=codigo, nome=nome, cidade=cidade, ativa=True))
            db.session.commit()
            flash("Base cadastrada.", "success")
            return redirect(url_for("admin.bases"))
    items = db.session.scalars(db.select(BaseOperacional).order_by(BaseOperacional.codigo)).all()
    return render_template("admin/bases.html", items=items)


@bp.route("/usuarios", methods=["GET", "POST"])
@login_required
@admin_required
def usuarios():
    bases = db.session.scalars(db.select(BaseOperacional).where(BaseOperacional.ativa.is_(True)).order_by(BaseOperacional.codigo)).all()
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        perfil = request.form.get("perfil", "ANALISTA")
        base_id = request.form.get("base_id", type=int)
        alterar_senha = request.form.get("alterar_senha") == "on"

        if not nome or not username or not base_id or not password or not confirm:
            flash("Preencha todos os campos obrigatórios, incluindo a senha inicial.", "warning")
        elif len(password) < 8:
            flash("A senha inicial deve ter pelo menos 8 caracteres.", "warning")
        elif password != confirm:
            flash("A senha inicial e a confirmação não conferem.", "warning")
        elif db.session.scalar(db.select(User).where(User.username == username)):
            flash("Esse login já existe.", "warning")
        else:
            user = User(
                nome=nome,
                username=username,
                perfil=perfil,
                base_id=base_id,
                ativo=True,
                alterar_senha=alterar_senha,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f"Usuário {username} criado com sucesso.", "success")
            return redirect(url_for("admin.usuarios"))
    items = db.session.scalars(db.select(User).order_by(User.nome)).all()
    return render_template("admin/usuarios.html", items=items, bases=bases)


@bp.post("/usuarios/<int:user_id>/resetar-senha")
@login_required
@admin_required
def resetar_senha(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        flash("Usuário não encontrado.", "warning")
        return redirect(url_for("admin.usuarios"))

    password = request.form.get("reset_password", "")
    confirm = request.form.get("reset_confirm", "")
    if len(password) < 8:
        flash("A nova senha deve ter pelo menos 8 caracteres.", "warning")
    elif password != confirm:
        flash("A nova senha e a confirmação não conferem.", "warning")
    else:
        user.set_password(password)
        user.alterar_senha = True
        db.session.commit()
        flash(f"Senha de {user.username} redefinida. O usuário deverá trocá-la no próximo acesso.", "success")
    return redirect(url_for("admin.usuarios"))


@bp.get("/plataforma")
@login_required
@admin_required
def plataforma():
    return render_template("admin/plataforma.html", health=platform_health())
