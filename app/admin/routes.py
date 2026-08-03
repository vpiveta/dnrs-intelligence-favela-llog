from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from app.core.decorators import admin_required
from app.extensions import db
from app.models import BaseOperacional, User
<<<<<<< HEAD
from app.core.platform import platform_health
=======
>>>>>>> 2de3bb5a2d6358c1527e18cfaffdfbc1dfc6baa8

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
        perfil = request.form.get("perfil", "ANALISTA")
        base_id = request.form.get("base_id", type=int)
        if not nome or not username or not base_id:
            flash("Preencha os campos obrigatórios.", "warning")
        elif db.session.scalar(db.select(User).where(User.username == username)):
            flash("Esse login já existe.", "warning")
        else:
            user = User(nome=nome, username=username, perfil=perfil, base_id=base_id, ativo=True, alterar_senha=True)
            user.set_password("Mudar@123")
            db.session.add(user)
            db.session.commit()
            flash("Usuário criado com senha temporária Mudar@123.", "success")
            return redirect(url_for("admin.usuarios"))
    items = db.session.scalars(db.select(User).order_by(User.nome)).all()
    return render_template("admin/usuarios.html", items=items, bases=bases)
<<<<<<< HEAD


@bp.get("/plataforma")
@login_required
@admin_required
def plataforma():
    return render_template("admin/plataforma.html", health=platform_health())
=======
>>>>>>> 2de3bb5a2d6358c1527e18cfaffdfbc1dfc6baa8
