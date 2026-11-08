from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user, login_required


def role_required(role):
    """Allow only logged-in users with the given role.

    Users with the wrong role are sent back to their own dashboard.
    """
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role != role:
                flash("Access denied for your account type.", "danger")
                return redirect(url_for("auth.dashboard"))
            return view(*args, **kwargs)
        return wrapper
    return decorator


def student_required(view):
    return role_required("student")(view)


def admin_required(view):
    return role_required("admin")(view)
