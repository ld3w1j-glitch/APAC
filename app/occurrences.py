from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .extensions import db
from .models import Occurrence, Visitor
from .access import roles_required

bp = Blueprint("occurrences", __name__)

@bp.route("/")
@login_required
@roles_required("seguranca", "gestao")
def index():
    occurrences = Occurrence.query.order_by(Occurrence.occurred_at.desc()).all()
    return render_template("occurrences/index.html", occurrences=occurrences)

@bp.route("/nova", methods=["GET", "POST"])
@login_required
@roles_required("seguranca", "gestao")
def create():
    visitors = Visitor.query.order_by(Visitor.full_name).all()
    if request.method == "POST":
        visitor = db.session.get(Visitor, int(request.form["visitor_id"]))
        occ = Occurrence(visitor=visitor, category=request.form["category"],
                         severity=request.form["severity"], description=request.form["description"],
                         action_taken=request.form.get("action_taken"), registered_by=current_user.username)
        if request.form.get("suspend_visitor") == "on":
            visitor.status = "suspenso"
        db.session.add(occ)
        db.session.commit()
        flash("Ocorrência registrada.", "success")
        return redirect(url_for("occurrences.index"))
    return render_template("occurrences/form.html", visitors=visitors)
