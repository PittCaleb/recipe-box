from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

bp = Blueprint("auth", __name__)

PROTECTED_BLUEPRINTS = {"edit", "admin", "share"}


def require_login():
    cfg = current_app.config["RECIPES_CONFIG"]
    if not cfg.APP_PASSWORD:
        return None
    if request.blueprint not in PROTECTED_BLUEPRINTS:
        return None
    if session.get("authenticated"):
        return None
    return redirect(url_for("auth.login", next=request.path))


@bp.route("/login", methods=["GET", "POST"])
def login():
    cfg = current_app.config["RECIPES_CONFIG"]
    if not cfg.APP_PASSWORD:
        return redirect(url_for("browse.index"))

    if request.method == "POST":
        if request.form.get("password") == cfg.APP_PASSWORD:
            session["authenticated"] = True
            next_url = request.form.get("next") or url_for("browse.index")
            return redirect(next_url)
        flash("Incorrect password.")

    return render_template("login.html", next=request.args.get("next", ""))


@bp.route("/logout", methods=["POST"])
def logout():
    session.pop("authenticated", None)
    return redirect(url_for("browse.index"))
