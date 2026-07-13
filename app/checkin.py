from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .extensions import db
from .models import Visitor, VisitLog

bp = Blueprint("checkin", __name__)

@bp.route("/")
@login_required
def index():
    active=VisitLog.query.filter_by(check_out=None).order_by(VisitLog.check_in.desc()).all()
    return render_template("checkin/index.html", active=active)

@bp.route("/buscar", methods=["POST"])
@login_required
def search():
    term=request.form.get("term", "").strip()
    visitor=Visitor.query.filter(db.or_(Visitor.cpf==term, Visitor.credential_code==term)).first()
    if not visitor:
        flash("Credencial ou CPF não encontrado.", "danger"); return redirect(url_for("checkin.index"))
    return redirect(url_for("visitors.detail", visitor_id=visitor.id))

@bp.route("/scan/<code>")
@login_required
def scan(code):
    visitor=Visitor.query.filter_by(credential_code=code).first_or_404()
    return redirect(url_for("visitors.detail", visitor_id=visitor.id))

@bp.route("/entrada/<int:visitor_id>", methods=["POST"])
@login_required
def enter(visitor_id):
    visitor=Visitor.query.get_or_404(visitor_id)
    if visitor.status != "ativo": flash("O visitante não está com status ativo.", "danger")
    elif not visitor.terms_accepted_at: flash("Registre o aceite das orientações antes da entrada.", "danger")
    elif VisitLog.query.filter_by(visitor_id=visitor.id, check_out=None).first(): flash("Este visitante já está dentro da unidade.", "warning")
    else:
        db.session.add(VisitLog(visitor_id=visitor.id, operator=current_user.username)); db.session.commit(); flash("Entrada registrada.", "success")
    return redirect(url_for("visitors.detail", visitor_id=visitor.id))

@bp.route("/saida/<int:log_id>", methods=["POST"])
@login_required
def leave(log_id):
    log=VisitLog.query.get_or_404(log_id); log.check_out=datetime.utcnow(); db.session.commit(); flash("Saída registrada.", "success")
    return redirect(url_for("checkin.index"))
