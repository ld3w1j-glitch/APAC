from datetime import datetime, timedelta
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from .models import Visitor, VisitLog, Appointment, MaterialEntry, Occurrence

bp = Blueprint("main", __name__)

@bp.route("/")
@login_required
def dashboard():
    if current_user.role == "usuario":
        from flask import redirect, url_for
        return redirect(url_for("portal.index"))
    today = datetime.now().date()
    start = datetime.combine(today, datetime.min.time())
    end = start + timedelta(days=1)
    visitors_total = Visitor.query.count()
    pending = Visitor.query.filter_by(status="pendente").count()
    active_inside = VisitLog.query.filter_by(check_out=None).count()
    visits_today = VisitLog.query.filter(VisitLog.check_in >= start, VisitLog.check_in < end).count()
    appointments_today = Appointment.query.filter(Appointment.scheduled_for >= start, Appointment.scheduled_for < end).count()
    materials_pending = MaterialEntry.query.filter_by(inspection_status="aguardando").count()
    occurrences_month = Occurrence.query.filter(Occurrence.occurred_at >= start.replace(day=1)).count()
    recent = Visitor.query.order_by(Visitor.created_at.desc()).limit(6).all()
    upcoming = Appointment.query.filter(Appointment.scheduled_for >= datetime.now(), Appointment.status.in_(["agendado", "confirmado"])).order_by(Appointment.scheduled_for).limit(5).all()
    return render_template("dashboard.html", visitors_total=visitors_total, pending=pending,
                           active_inside=active_inside, visits_today=visits_today,
                           appointments_today=appointments_today, materials_pending=materials_pending,
                           occurrences_month=occurrences_month, recent=recent, upcoming=upcoming)
