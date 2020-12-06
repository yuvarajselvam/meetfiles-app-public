import logging

from flask import Blueprint, jsonify
from flask_login import current_user

from app.extensions import firebase_service

logger = logging.getLogger(__name__)
api = Blueprint('notifications', __name__, url_prefix='/api/v1/notifications')


def list_notifications():
    notifications = firebase_service.get_notifications(current_user.id)
    to_ret = []
    if not notifications:
        return jsonify([]), 204
    for k, v in notifications.items():
        v["id"] = k
        to_ret.append(v)
    return jsonify(to_ret), 200


def mark_all_as_read():
    notifications = firebase_service.get_notifications(current_user.id, read=False)
    update_obj = {}
    for k, v in notifications:
        update_obj[f"users/{current_user.id}/notifications/{k}/isRead"] = True
    firebase_service.db_update(update_obj)
    return notifications, 200


api.add_url_rule('/', view_func=list_notifications)
api.add_url_rule('/', view_func=mark_all_as_read, methods=['POST'])
