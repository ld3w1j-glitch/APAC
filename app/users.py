from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from .extensions import db
from .models import User
from .access import roles_required

bp = Blueprint("users", __name__)

@bp.route("/")
@login_required
@roles_required("admin")
def index():
    return render_template("users/index.html", users=User.query.order_by(User.username).all())

@bp.route("/novo", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def create():
    if request.method == "POST":
        username = request.form["username"].strip()
        if User.query.filter_by(username=username).first():
            flash("Esse usuário já existe.", "danger")
            return redirect(url_for("users.create"))
        user = User(username=username, full_name=request.form.get("full_name"),
                    password_hash=generate_password_hash(request.form["password"]),
                    role=request.form["role"])
        db.session.add(user)
        db.session.commit()
        flash("Usuário criado.", "success")
        return redirect(url_for("users.index"))
    return render_template("users/form.html")

@bp.post("/<int:user_id>/toggle")
@login_required
@roles_required("admin")
def toggle(user_id):
    user = db.get_or_404(User, user_id)
    user.active = not user.active
    db.session.commit()
    flash("Acesso do usuário atualizado.", "success")
    return redirect(url_for("users.index"))

@bp.post("/<int:user_id>/excluir")
@login_required
@roles_required("admin")
def delete(user_id):
    user = db.get_or_404(User, user_id)

    if user.id == current_user.id:
        flash("Você não pode excluir o usuário que está conectado.", "danger")
        return redirect(url_for("users.index"))

    if user.role == "admin" and user.active:
        active_admins = User.query.filter_by(role="admin", active=True).count()
        if active_admins <= 1:
            flash("Não é possível excluir o último administrador ativo.", "danger")
            return redirect(url_for("users.index"))

    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f"Usuário {username} excluído permanentemente.", "success")
    return redirect(url_for("users.index"))
