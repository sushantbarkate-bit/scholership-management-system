from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from services import notification_service as notes


notification_bp = Blueprint("notification", __name__, url_prefix="/notifications")


@notification_bp.route("/")
@login_required
def index():
    page = request.args.get("page", 1, type=int) or 1
    pagination = notes.list_for_user(current_user.id, page, per_page=10)
    return render_template("notifications/index.html", pagination=pagination)


@notification_bp.route("/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_read(notification_id):
    if not notes.mark_read(notification_id, current_user.id):
        flash("Notification not found.", "danger")
    return redirect(url_for("notification.index"))


@notification_bp.route("/read-all", methods=["POST"])
@login_required
def mark_all_read():
    notes.mark_all_read(current_user.id)
    flash("All notifications marked as read.", "success")
    return redirect(url_for("notification.index"))
