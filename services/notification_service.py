from extensions import db
from models import Notification


def notify(user_id, title, message):
    """Queue a notification in the current session. Caller commits."""
    notification = Notification(user_id=user_id, title=title, message=message)
    db.session.add(notification)
    return notification


def unread_count(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def list_for_user(user_id, page, per_page):
    return (
        Notification.query
        .filter_by(user_id=user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )


def mark_read(notification_id, user_id):
    notification = db.session.get(Notification, notification_id)
    if notification is None or notification.user_id != user_id:
        return False
    notification.is_read = True
    db.session.commit()
    return True


def mark_all_read(user_id):
    Notification.query.filter_by(user_id=user_id, is_read=False).update(
        {"is_read": True}, synchronize_session=False
    )
    db.session.commit()
