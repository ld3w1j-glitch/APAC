from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from .models import User

bp = Blueprint("auth", __name__)

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username", "").strip()).first()
        if user and user.active and check_password_hash(user.password_hash, request.form.get("password", "")):
            login_user(user)
            if user.role == "usuario":
                return redirect(url_for("portal.index"))
            return redirect(url_for("main.dashboard"))
        flash("Usuário, senha ou acesso inválido.", "danger")
    return render_template("auth/login.html")

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
