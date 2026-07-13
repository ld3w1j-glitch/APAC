from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .extensions import db
from .models import Appointment, Visitor

bp = Blueprint("appointments", __name__)

@bp.route("/")
@login_required
def index():
    status = request.args.get("status", "")
    q = Appointment.query
    if status:
        q = q.filter_by(status=status)
    appointments = q.order_by(Appointment.scheduled_for.asc()).all()
    return render_template("appointments/index.html", appointments=appointments, status=status)

@bp.route("/novo", methods=["GET", "POST"])
@login_required
def create():
    visitors = Visitor.query.filter_by(status="ativo").order_by(Visitor.full_name).all()
    if request.method == "POST":
        visitor = db.session.get(Visitor, int(request.form["visitor_id"]))
        if not visitor:
            flash("Visitante não encontrado.", "danger")
            return redirect(url_for("appointments.create"))
        scheduled_for = datetime.fromisoformat(request.form["scheduled_for"])
        appointment = Appointment(visitor=visitor, scheduled_for=scheduled_for,
                                  notes=request.form.get("notes"), created_by=current_user.username)
        db.session.add(appointment)
        db.session.commit()
        flash("Visita agendada com sucesso.", "success")
        return redirect(url_for("appointments.index"))
    return render_template("appointments/form.html", visitors=visitors)

@bp.post("/<int:appointment_id>/status")
@login_required
def change_status(appointment_id):
    appointment = db.get_or_404(Appointment, appointment_id)
    new_status = request.form.get("status")
    if new_status in {"agendado", "confirmado", "realizado", "cancelado"}:
        appointment.status = new_status
        db.session.commit()
        flash("Status atualizado.", "success")
    return redirect(url_for("appointments.index"))
