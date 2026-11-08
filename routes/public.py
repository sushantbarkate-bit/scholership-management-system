from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

from models import Scholarship


public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))
    active = Scholarship.query.filter_by(is_active=True).count()
    return render_template("public/landing.html", active_scholarships=active)


@public_bp.route("/about")
def about():
    return render_template("public/about.html")
