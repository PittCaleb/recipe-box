import os

from flask import Flask, g
from werkzeug.middleware.proxy_fix import ProxyFix

from config import config as default_config
from app.db import get_connection, run_migrations


def create_app(config_obj=None):
    cfg = config_obj or default_config
    cfg.ensure_data_dirs()
    run_migrations(cfg.DB_PATH)

    app = Flask(__name__)
    app.config["RECIPES_CONFIG"] = cfg
    # Behind the NAS reverse proxy the app lives at /recipes: the proxy sends
    # X-Forwarded-Prefix and url_for() builds every link under it. Run
    # directly, there's no header and nothing changes.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    # Other apps share the NAS hostname; a distinct cookie name keeps their
    # Flask sessions from overwriting ours.
    app.config["SESSION_COOKIE_NAME"] = "recipes_session"

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    # The session only carries flash messages; a fixed key (set in the
    # container's env) keeps them working across restarts.
    import secrets
    app.secret_key = os.environ.get("RECIPES_SECRET_KEY") or secrets.token_hex(32)

    from app.routes.browse import bp as browse_bp
    from app.routes.recipe import bp as recipe_bp
    from app.routes.media import bp as media_bp
    from app.routes.edit import bp as edit_bp
    from app.routes.admin import bp as admin_bp
    from app.routes.share import bp as share_bp
    from app.routes.import_pdf import bp as import_pdf_bp
    from app.routes.duplicates import bp as duplicates_bp
    from app.routes.help import bp as help_bp
    from app.routes.api import bp as api_bp
    app.register_blueprint(browse_bp)
    app.register_blueprint(recipe_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(edit_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(share_bp)
    app.register_blueprint(import_pdf_bp)
    app.register_blueprint(duplicates_bp)
    app.register_blueprint(help_bp)
    app.register_blueprint(api_bp)

    from app import users
    app.before_request(users.load_user)

    @app.errorhandler(403)
    def forbidden(exc):
        from flask import render_template
        return render_template("forbidden.html", message=exc.description), 403

    from app.images import thumb_filename
    app.jinja_env.globals["thumb_filename"] = thumb_filename

    @app.context_processor
    def inject_permissions():
        return {
            "current_user": users.current_user(),
            "is_admin": users.is_admin(),
            "can_edit_recipe": users.can_edit_recipe,
            "can_delete_recipe": users.can_delete_recipe,
            "can_delete_note": users.can_delete_note,
            "can_draw_pictures": bool(cfg.ANTHROPIC_API_KEY),
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
