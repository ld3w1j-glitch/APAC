import os
from flask import Flask
from .extensions import db, login_manager


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-me")
    database_url = os.getenv("DATABASE_URL", "sqlite:///apac_visitas.db")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para continuar."

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from .auth import bp as auth_bp
    from .main import bp as main_bp
    from .visitors import bp as visitors_bp
    from .checkin import bp as checkin_bp
    from .reports import bp as reports_bp
    from .orientation import bp as orientation_bp
    from .appointments import bp as appointments_bp
    from .materials import bp as materials_bp
    from .occurrences import bp as occurrences_bp
    from .users import bp as users_bp
    from .portal import bp as portal_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(visitors_bp, url_prefix="/visitantes")
    app.register_blueprint(checkin_bp, url_prefix="/portaria")
    app.register_blueprint(reports_bp, url_prefix="/relatorios")
    app.register_blueprint(orientation_bp, url_prefix="/orientacoes")
    app.register_blueprint(appointments_bp, url_prefix="/agendamentos")
    app.register_blueprint(materials_bp, url_prefix="/materiais")
    app.register_blueprint(occurrences_bp, url_prefix="/ocorrencias")
    app.register_blueprint(users_bp, url_prefix="/usuarios")
    app.register_blueprint(portal_bp)

    with app.app_context():
        db.create_all()
        from werkzeug.security import generate_password_hash
        admin_user = os.getenv("ADMIN_USER", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        if not User.query.filter_by(username=admin_user).first():
            db.session.add(User(username=admin_user, full_name="Administrador",
                                password_hash=generate_password_hash(admin_password), role="admin"))
            db.session.commit()

        visitor_user = os.getenv("VISITOR_USER", "visitante")
        visitor_password = os.getenv("VISITOR_PASSWORD", "visitante123")
        if not User.query.filter_by(username=visitor_user).first():
            db.session.add(User(username=visitor_user, full_name="Visitante",
                                password_hash=generate_password_hash(visitor_password), role="usuario"))
            db.session.commit()

    from flask import request, redirect, url_for
    from flask_login import current_user

    @app.before_request
    def restrict_user_area():
        if not current_user.is_authenticated or current_user.role != "usuario":
            return None
        allowed = {"portal.index", "auth.logout", "static"}
        if request.endpoint not in allowed:
            return redirect(url_for("portal.index"))

    return app
