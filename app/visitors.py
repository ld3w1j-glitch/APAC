import os, uuid, io
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from flask_login import login_required
from werkzeug.utils import secure_filename
import qrcode
from PIL import Image as PILImage, ImageOps
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from .extensions import db
from .models import Visitor, VisitorDocuments

bp = Blueprint("visitors", __name__)
ALLOWED = {"png", "jpg", "jpeg", "webp"}


def allowed_file(name):
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED


def _qr_image(visitor):
    """Gera o QR Code que aponta para a tela de conferência da portaria."""
    scan_url = url_for("checkin.scan", code=visitor.credential_code, _external=True)
    qr = qrcode.QRCode(version=None, box_size=10, border=2)
    qr.add_data(scan_url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def _fit_photo(path, size=(720, 900)):
    """Abre e recorta a foto em proporção de credencial, evitando deformação."""
    image = PILImage.open(path).convert("RGB")
    return ImageOps.fit(image, size, method=PILImage.Resampling.LANCZOS)


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
        flash("Visitante cadastrado com sucesso. A credencial em PDF já pode ser gerada.", "success")
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
    img = _qr_image(visitor)
    buf=io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    return send_file(buf, mimetype="image/png")


@bp.route("/<int:visitor_id>/credencial.pdf")
@login_required
def credential_pdf(visitor_id):
    """Gera folha A4 com credencial pronta para recorte e plastificação."""
    visitor = Visitor.query.get_or_404(visitor_id)
    buffer = io.BytesIO()
    page_w, page_h = landscape(A4)
    pdf = canvas.Canvas(buffer, pagesize=(page_w, page_h))
    pdf.setTitle(f"Credencial - {visitor.full_name}")

    # Dimensões ampliadas para facilitar impressão, recorte e leitura do QR.
    card_w, card_h = 360, 230
    card_x = (page_w - card_w) / 2
    card_y = (page_h - card_h) / 2 + 20
    blue = colors.HexColor("#103B66")
    light_blue = colors.HexColor("#1D71BB")

    # Instrução de impressão.
    pdf.setFillColor(colors.HexColor("#506B83"))
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(page_w / 2, page_h - 38, "Imprima em tamanho real (100%), recorte na linha pontilhada e plastifique.")

    # Linha de corte.
    pdf.setDash(4, 3)
    pdf.setStrokeColor(colors.HexColor("#7893AA"))
    pdf.roundRect(card_x - 8, card_y - 8, card_w + 16, card_h + 16, 14, stroke=1, fill=0)
    pdf.setDash()

    # Fundo da credencial.
    pdf.setFillColor(colors.white)
    pdf.setStrokeColor(blue)
    pdf.setLineWidth(2)
    pdf.roundRect(card_x, card_y, card_w, card_h, 12, stroke=1, fill=1)
    pdf.setFillColor(blue)
    pdf.roundRect(card_x, card_y + card_h - 48, card_w, 48, 12, stroke=0, fill=1)
    pdf.rect(card_x, card_y + card_h - 48, card_w, 24, stroke=0, fill=1)

    # Logo.
    logo_path = os.path.join(current_app.root_path, "static", "img", "logo_apac.png")
    if os.path.exists(logo_path):
        pdf.drawImage(logo_path, card_x + 12, card_y + card_h - 43, width=42, height=35,
                      preserveAspectRatio=True, mask="auto", anchor="c")
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawString(card_x + 60, card_y + card_h - 30, "CREDENCIAL DE VISITANTE")

    # Foto.
    photo_x, photo_y, photo_w, photo_h = card_x + 18, card_y + 38, 92, 116
    pdf.setStrokeColor(colors.HexColor("#B7CADB"))
    pdf.setFillColor(colors.HexColor("#EEF4F9"))
    pdf.roundRect(photo_x, photo_y, photo_w, photo_h, 7, stroke=1, fill=1)
    if visitor.photo_filename:
        photo_path = os.path.join(current_app.config["UPLOAD_FOLDER"], visitor.photo_filename)
        if os.path.exists(photo_path):
            photo = _fit_photo(photo_path)
            photo_buf = io.BytesIO(); photo.save(photo_buf, format="JPEG", quality=92); photo_buf.seek(0)
            pdf.drawImage(ImageReader(photo_buf), photo_x, photo_y, width=photo_w, height=photo_h, mask="auto")
    else:
        pdf.setFillColor(colors.HexColor("#607D98")); pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(photo_x + photo_w/2, photo_y + photo_h/2, "SEM FOTO")

    # QR Code em uma coluna exclusiva, sem sobrepor os dados do visitante.
    qr_img = _qr_image(visitor)
    qr_buf = io.BytesIO(); qr_img.save(qr_buf, format="PNG"); qr_buf.seek(0)
    qr_size = 78
    qr_x = card_x + card_w - qr_size - 14
    qr_y = card_y + 36

    # Linha divisória entre informações e QR Code.
    divider_x = qr_x - 10
    pdf.setStrokeColor(colors.HexColor("#D5E1EB"))
    pdf.setLineWidth(0.8)
    pdf.line(divider_x, card_y + 28, divider_x, card_y + card_h - 62)

    # Informações com largura limitada até a coluna do QR Code.
    info_x = card_x + 126
    info_y = card_y + card_h - 76
    label_width = 65
    value_x = info_x + label_width
    value_max_width = divider_x - value_x - 6

    def fit_text(value, font_name, font_size, max_width):
        value = str(value or "-")
        if stringWidth(value, font_name, font_size) <= max_width:
            return value
        suffix = "..."
        while value and stringWidth(value + suffix, font_name, font_size) > max_width:
            value = value[:-1]
        return value + suffix if value else suffix

    pdf.setFillColor(blue)
    pdf.setFont("Helvetica-Bold", 15)
    name_max_width = divider_x - info_x - 6
    pdf.drawString(info_x, info_y, fit_text(visitor.full_name, "Helvetica-Bold", 15, name_max_width))

    rows = [
        ("CPF", visitor.cpf),
        ("Recuperando", visitor.resident_name),
        ("Parentesco", visitor.relationship or "-"),
        ("Validade", visitor.credential_valid_until.strftime("%d/%m/%Y") if visitor.credential_valid_until else "Sem data definida"),
        ("Status", visitor.status.upper()),
    ]
    y = info_y - 24
    for label, value in rows:
        pdf.setFont("Helvetica-Bold", 9); pdf.setFillColor(colors.HexColor("#506B83"))
        pdf.drawString(info_x, y, f"{label}:")
        pdf.setFont("Helvetica", 9); pdf.setFillColor(colors.HexColor("#17324D"))
        pdf.drawString(value_x, y, fit_text(value, "Helvetica", 9, value_max_width))
        y -= 18

    pdf.drawImage(ImageReader(qr_buf), qr_x, qr_y, width=qr_size, height=qr_size, mask="auto")
    pdf.setFillColor(light_blue); pdf.setFont("Helvetica-Bold", 7)
    pdf.drawCentredString(qr_x + qr_size/2, qr_y - 9, "ESCANEIE PARA CONFERIR")

    # Código e aviso.
    pdf.setFillColor(colors.HexColor("#607D98")); pdf.setFont("Helvetica", 7)
    pdf.drawString(card_x + 18, card_y + 17, f"Código: {visitor.credential_code}")
    pdf.setFillColor(blue); pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(card_x + 18, card_y + 6, "Documento pessoal e intransferível.")

    # Rodapé da folha.
    pdf.setFillColor(colors.HexColor("#506B83")); pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(page_w / 2, 28, f"APAC de Pouso Alegre - MG | Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    pdf.showPage(); pdf.save(); buffer.seek(0)
    safe_name = secure_filename(visitor.full_name) or f"visitante_{visitor.id}"
    return send_file(buffer, mimetype="application/pdf", as_attachment=True,
                     download_name=f"credencial_{safe_name}.pdf")


@bp.route("/<int:visitor_id>/excluir", methods=["POST"])
@login_required
def delete(visitor_id):
    visitor=Visitor.query.get_or_404(visitor_id); db.session.delete(visitor); db.session.commit(); flash("Visitante excluído.", "success")
    return redirect(url_for("visitors.index"))
