import logging

from flask import Blueprint, request
from flask_login import current_user

from app.extensions import firebase_service

logger = logging.getLogger(__name__)
api = Blueprint('notifications', __name__, url_prefix='/api/v1/notifications')


def mark_all_as_read():
    firebase_service.notify(current_user.id, "Get Notifications Test", "This is a test")
    notifications = firebase_service.get_notifications(current_user.id)
    print(notifications)
    return notifications, 200


api.add_url_rule('/', view_func=mark_all_as_read)
