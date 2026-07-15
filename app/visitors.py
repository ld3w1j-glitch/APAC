import os, uuid, io
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from flask_login import login_required
from werkzeug.utils import secure_filename
import qrcode
from .extensions import db
from .models import Visitor, VisitorDocuments
from .access import roles_required

bp = Blueprint("visitors", __name__)
ALLOWED = {"png", "jpg", "jpeg", "webp"}

def allowed_file(name):
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED

@bp.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    query = Visitor.query
    if q:
        query = query.filter(db.or_(Visitor.full_name.ilike(f"%{q}%"), Visitor.cpf.ilike(f"%{q}%"), Visitor.resident_name.ilike(f"%{q}%")))
    return render_template("visitors/index.html", visitors=query.order_by(Visitor.full_name).all(), q=q)

@bp.route("/novo", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        cpf = request.form["cpf"].strip()
        if Visitor.query.filter_by(cpf=cpf).first():
            flash("Já existe um visitante com este CPF.", "danger")
            return render_template("visitors/form.html", visitor=None)
        photo = request.files.get("photo")
        photo_name = None
        if photo and photo.filename and allowed_file(photo.filename):
            photo_name = f"{uuid.uuid4().hex}_{secure_filename(photo.filename)}"
            photo.save(os.path.join(current_app.config["UPLOAD_FOLDER"], photo_name))
        birth_date = request.form.get("birth_date") or None
        valid_until = request.form.get("credential_valid_until") or None
        visitor = Visitor(
            full_name=request.form["full_name"].strip(), cpf=cpf, phone=request.form.get("phone"),
            address=request.form.get("address"), relationship=request.form.get("relationship"),
            resident_name=request.form["resident_name"].strip(),
            birth_date=datetime.strptime(birth_date, "%Y-%m-%d").date() if birth_date else None,
            credential_valid_until=datetime.strptime(valid_until, "%Y-%m-%d").date() if valid_until else None,
            status=request.form.get("status", "pendente"), photo_filename=photo_name,
            credential_code=uuid.uuid4().hex, notes=request.form.get("notes")
        )
        db.session.add(visitor); db.session.flush()
        docs = VisitorDocuments(visitor_id=visitor.id)
        for field in ["registration_form","photo_3x4","proof_of_address","identity_copy","marriage_or_union","originals_checked"]:
            setattr(docs, field, bool(request.form.get(field)))
        db.session.add(docs); db.session.commit()
        flash("Visitante cadastrado com sucesso.", "success")
        return redirect(url_for("visitors.detail", visitor_id=visitor.id))
    return render_template("visitors/form.html", visitor=None)

@bp.route("/<int:visitor_id>")
@login_required
def detail(visitor_id):
    return render_template("visitors/detail.html", visitor=Visitor.query.get_or_404(visitor_id))

@bp.route("/<int:visitor_id>/editar", methods=["GET", "POST"])
@login_required
def edit(visitor_id):
    visitor = Visitor.query.get_or_404(visitor_id)
    if request.method == "POST":
        visitor.full_name=request.form["full_name"].strip(); visitor.cpf=request.form["cpf"].strip()
        visitor.phone=request.form.get("phone"); visitor.address=request.form.get("address")
        visitor.relationship=request.form.get("relationship"); visitor.resident_name=request.form["resident_name"].strip()
        visitor.status=request.form.get("status", "pendente"); visitor.notes=request.form.get("notes")
        valid_until=request.form.get("credential_valid_until") or None
        visitor.credential_valid_until=datetime.strptime(valid_until, "%Y-%m-%d").date() if valid_until else None
        photo=request.files.get("photo")
        if photo and photo.filename and allowed_file(photo.filename):
            photo_name=f"{uuid.uuid4().hex}_{secure_filename(photo.filename)}"; photo.save(os.path.join(current_app.config["UPLOAD_FOLDER"], photo_name)); visitor.photo_filename=photo_name
        docs=visitor.documents or VisitorDocuments(visitor_id=visitor.id)
        for field in ["registration_form","photo_3x4","proof_of_address","identity_copy","marriage_or_union","originals_checked"]:
            setattr(docs, field, bool(request.form.get(field)))
        db.session.add(docs); db.session.commit(); flash("Cadastro atualizado.", "success")
        return redirect(url_for("visitors.detail", visitor_id=visitor.id))
    return render_template("visitors/form.html", visitor=visitor)

@bp.route("/<int:visitor_id>/aceite", methods=["POST"])
@login_required
def accept_terms(visitor_id):
    visitor=Visitor.query.get_or_404(visitor_id); visitor.terms_accepted_at=datetime.utcnow(); db.session.commit(); flash("Termo de ciência registrado.", "success")
    return redirect(url_for("visitors.detail", visitor_id=visitor.id))

@bp.route("/<int:visitor_id>/qrcode")
@login_required
def qr(visitor_id):
    visitor=Visitor.query.get_or_404(visitor_id)
    img=qrcode.make(url_for("checkin.scan", code=visitor.credential_code, _external=True))
    buf=io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    return send_file(buf, mimetype="image/png")

@bp.route("/<int:visitor_id>/excluir", methods=["POST"])
@login_required
@roles_required("admin")
def delete(visitor_id):
    visitor = Visitor.query.get_or_404(visitor_id)
    visitor_name = visitor.full_name
    photo_filename = visitor.photo_filename

    db.session.delete(visitor)
    db.session.commit()

    # Remove também a fotografia armazenada, quando existir.
    if photo_filename:
        photo_path = os.path.join(current_app.config["UPLOAD_FOLDER"], photo_filename)
        try:
            if os.path.isfile(photo_path):
                os.remove(photo_path)
        except OSError:
            current_app.logger.warning("Não foi possível remover a foto do visitante: %s", photo_path)

    flash(f"Visitante {visitor_name} excluído permanentemente.", "success")
    return redirect(url_for("visitors.index"))
