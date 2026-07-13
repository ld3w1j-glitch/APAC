from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .extensions import db
from .models import MaterialEntry, Visitor

bp = Blueprint("materials", __name__)

@bp.route("/")
@login_required
def index():
    status = request.args.get("status", "")
    q = MaterialEntry.query
    if status:
        q = q.filter_by(inspection_status=status)
    items = q.order_by(MaterialEntry.created_at.desc()).all()
    return render_template("materials/index.html", items=items, status=status)

@bp.route("/novo", methods=["GET", "POST"])
@login_required
def create():
    visitors = Visitor.query.order_by(Visitor.full_name).all()
    if request.method == "POST":
        visitor = db.session.get(Visitor, int(request.form["visitor_id"]))
        item = MaterialEntry(visitor=visitor, resident_name=visitor.resident_name,
                             description=request.form["description"], quantity=request.form.get("quantity"),
                             notes=request.form.get("notes"))
        db.session.add(item)
        db.session.commit()
        flash("Material registrado para vistoria.", "success")
        return redirect(url_for("materials.index"))
    return render_template("materials/form.html", visitors=visitors)

@bp.post("/<int:item_id>/vistoriar")
@login_required
def inspect(item_id):
    item = db.get_or_404(MaterialEntry, item_id)
    status = request.form.get("inspection_status")
    if status in {"aprovado", "recusado"}:
        item.inspection_status = status
        item.inspector = current_user.username
        item.inspected_at = datetime.utcnow()
        item.notes = request.form.get("notes") or item.notes
        db.session.commit()
        flash("Vistoria registrada.", "success")
    return redirect(url_for("materials.index"))
