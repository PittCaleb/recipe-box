from flask import Flask, g

from config import config as default_config
from app.db import get_connection, run_migrations


def create_app(config_obj=None):
    cfg = config_obj or default_config
    cfg.ensure_data_dirs()
    run_migrations(cfg.DB_PATH)

    app = Flask(__name__)
    app.config["RECIPES_CONFIG"] = cfg

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    import secrets
    app.secret_key = secrets.token_hex(32)

    from app.routes.browse import bp as browse_bp
    from app.routes.recipe import bp as recipe_bp
    from app.routes.media import bp as media_bp
    from app.routes.edit import bp as edit_bp
    from app.routes.admin import bp as admin_bp
    from app.routes.share import bp as share_bp
    from app.routes.import_pdf import bp as import_pdf_bp
    from app.routes.auth import bp as auth_bp, require_login
    app.register_blueprint(browse_bp)
    app.register_blueprint(recipe_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(edit_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(share_bp)
    app.register_blueprint(import_pdf_bp)
    app.register_blueprint(auth_bp)

    app.before_request(require_login)

    from app.images import thumb_filename
    app.jinja_env.globals["thumb_filename"] = thumb_filename

    @app.context_processor
    def inject_auth_state():
        from flask import session
        return {
            "login_required": bool(cfg.APP_PASSWORD),
            "is_authenticated": bool(session.get("authenticated")) or not cfg.APP_PASSWORD,
        }

    @app.template_filter("fmtdate")
    def fmtdate(value):
        if not value:
            return ""
        from datetime import datetime
        try:
            return datetime.fromisoformat(value).strftime("%b %-d, %Y")
        except ValueError:
            return value

    return app


def get_db():
    if "db" not in g:
        from flask import current_app
        cfg = current_app.config["RECIPES_CONFIG"]
        g.db = get_connection(cfg.DB_PATH)
    return g.db
