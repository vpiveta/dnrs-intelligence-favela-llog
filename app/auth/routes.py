from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from app.extensions import db
from app.models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = db.session.scalar(db.select(User).where(User.username == username))
        if user and user.check_password(password) and user.ativo:
            login_user(user, remember=bool(request.form.get("remember")))
            if user.alterar_senha:
                return redirect(url_for("auth.change_password"))
            return redirect(url_for("dashboard.index"))
        flash("Usuário ou senha inválidos.", "danger")
    return render_template("auth/login.html")


@bp.route("/alterar-senha", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if len(password) < 8:
            flash("A senha deve ter pelo menos 8 caracteres.", "warning")
        elif password != confirm:
            flash("As senhas não conferem.", "warning")
        else:
            current_user.set_password(password)
            current_user.alterar_senha = False
            db.session.commit()
            flash("Senha atualizada com sucesso.", "success")
            return redirect(url_for("dashboard.index"))
    return render_template("auth/change_password.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
