from datetime import datetime
from flask_login import UserMixin
from .extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(140))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default="cadastro")
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_active(self):
        return bool(self.active)


class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(180), nullable=False)
    cpf = db.Column(db.String(20), unique=True, nullable=False)
    phone = db.Column(db.String(30))
    address = db.Column(db.String(255))
    relationship = db.Column(db.String(80))
    resident_name = db.Column(db.String(180), nullable=False)
    birth_date = db.Column(db.Date)
    photo_filename = db.Column(db.String(255))
    credential_code = db.Column(db.String(64), unique=True, nullable=False)
    credential_valid_until = db.Column(db.Date)
    status = db.Column(db.String(30), default="pendente")
    terms_accepted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    documents = db.relationship("VisitorDocuments", backref="visitor", uselist=False, cascade="all, delete-orphan")
    visits = db.relationship("VisitLog", backref="visitor", cascade="all, delete-orphan")
    appointments = db.relationship("Appointment", backref="visitor", cascade="all, delete-orphan")
    materials = db.relationship("MaterialEntry", backref="visitor", cascade="all, delete-orphan")
    occurrences = db.relationship("Occurrence", backref="visitor", cascade="all, delete-orphan")


class VisitorDocuments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.Integer, db.ForeignKey("visitor.id"), unique=True, nullable=False)
    registration_form = db.Column(db.Boolean, default=False)
    photo_3x4 = db.Column(db.Boolean, default=False)
    proof_of_address = db.Column(db.Boolean, default=False)
    identity_copy = db.Column(db.Boolean, default=False)
    marriage_or_union = db.Column(db.Boolean, default=False)
    originals_checked = db.Column(db.Boolean, default=False)

    @property
    def complete(self):
        return all([self.registration_form, self.photo_3x4, self.proof_of_address, self.identity_copy, self.originals_checked])


class VisitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.Integer, db.ForeignKey("visitor.id"), nullable=False)
    check_in = db.Column(db.DateTime, default=datetime.utcnow)
    check_out = db.Column(db.DateTime)
    operator = db.Column(db.String(80))
    observations = db.Column(db.Text)

    @property
    def is_open(self):
        return self.check_out is None


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.Integer, db.ForeignKey("visitor.id"), nullable=False)
    scheduled_for = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(30), default="agendado")
    notes = db.Column(db.Text)
    created_by = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MaterialEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.Integer, db.ForeignKey("visitor.id"), nullable=False)
    resident_name = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    quantity = db.Column(db.String(50))
    inspection_status = db.Column(db.String(30), default="aguardando")
    inspector = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    inspected_at = db.Column(db.DateTime)


class Occurrence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.Integer, db.ForeignKey("visitor.id"), nullable=False)
    occurred_at = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(80), nullable=False)
    severity = db.Column(db.String(30), default="leve")
    description = db.Column(db.Text, nullable=False)
    action_taken = db.Column(db.Text)
    registered_by = db.Column(db.String(100))
