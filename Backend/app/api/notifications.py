import logging

from flask_login import current_user
from flask import Blueprint, request, jsonify

from app.utils.precheck import precheck
from app.models.notification import Notification

logger = logging.getLogger(__name__)
api = Blueprint('notifications', __name__, url_prefix='/api/v1/notifications')


@precheck(required_fields=['token'])
def subscribe():
    req_json = request.get_json()
    current_user.notifTokens.append(req_json["token"])
    current_user.save()
    return {"message": "Successfully subscribed to notifications"}, 200


@precheck(required_fields=['token'])
def unsubscribe():
    req_json = request.get_json()
    try:
        current_user.notifTokens.remove(req_json["token"])
    except ValueError:
        pass
    else:
        current_user.save()
    return {"message": "Successfully unsubscribed from notifications"}, 200


def list_notifications():
    notifications = Notification.find({"user": current_user.id})
    result = []
    for notif in notifications:
        notif.pop("_id")
        result.append(notif)
    return jsonify(notifications), 200


@precheck(required_fields=['id'])
def read_notification():
    req_json = request.get_json()
    query = {"user": current_user.id, "id": req_json["id"]}
    notif = Notification.find_one(query)
    notif.isRead = True
    notif.save()
    return notif.json(), 200
