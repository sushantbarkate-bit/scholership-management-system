import os

from flask import Flask, render_template, request, url_for
from flask_login import LoginManager, current_user
from sqlalchemy import text

from config import Config
from extensions import db

from flask_wtf.csrf import CSRFProtect

from flask_migrate import Migrate


login_manager = LoginManager()

csrf = CSRFProtect()


def create_app(test_config=None):

    app = Flask(__name__)

    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "documents"), exist_ok=True)

    # Initialize database
    db.init_app(app)

    Migrate(app, db)

    csrf.init_app(app)

    # Initialize login manager
    login_manager.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please login to access this page."
    login_manager.login_message_category = "warning"

    # Import models
    from models import User

    # Load logged-in user
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from routes.public import public_bp
    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.scholarship import scholarship_bp
    from routes.application import application_bp
    from routes.document import document_bp
    from routes.notification import notification_bp
    from routes.admin import admin_bp
    from routes.report import report_bp

    for blueprint in (public_bp, auth_bp, student_bp, scholarship_bp,
                      application_bp, document_bp, notification_bp,
                      admin_bp, report_bp):
        app.register_blueprint(blueprint)

    def page_url(page_number):
        """Current URL with the same filters and a different page number."""
        args = request.args.to_dict()
        args["page"] = page_number
        return url_for(request.endpoint, **args)

    app.jinja_env.globals["page_url"] = page_url

    # Values available to every template (navbar badge, status labels).
    @app.context_processor
    def inject_globals():
        from services.constants import APPLICATION_STATUSES, DOCUMENT_TYPE_LABELS
        from services.notification_service import unread_count

        unread = 0
        if current_user.is_authenticated:
            unread = unread_count(current_user.id)
        return {
            "unread_notifications": unread,
            "APPLICATION_STATUSES": APPLICATION_STATUSES,
            "DOCUMENT_TYPE_LABELS": DOCUMENT_TYPE_LABELS,
        }

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(413)
    def too_large(error):
        return render_template(
            "errors/generic.html",
            title="File too large",
            message="The upload exceeds the size limit. Please upload a smaller file.",
        ), 413

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template(
            "errors/generic.html",
            title="Something went wrong",
            message="An unexpected error occurred. Please try again.",
        ), 500

    @app.route("/test-db")
    def test_db():

        try:
            with db.engine.connect() as connection:
                connection.execute(text("SELECT 1"))

            return "MySQL Database Connected Successfully!"

        except Exception:
            app.logger.exception("Database connection check failed")
            return "Database connection failed. See server logs.", 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
