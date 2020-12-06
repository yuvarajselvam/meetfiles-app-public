import logging

from flask import Blueprint, request

from app.models.user import User

logger = logging.getLogger(__name__)
api = Blueprint('sync', __name__, url_prefix='/api/v1/sync')


def google_sync():
    headers = request.headers
    user_id = headers.get("X-Goog-Channel-Token")
    exp = headers.get("X-Goog-Channel-Expiration")
    user = User.find_one({"id": user_id})
    account = user.get_primary_account()
    calendar = account.get_calendar()
    calendar.notifChannel["expiration"] = exp
    calendar.sync_events()
    calendar.save()
    return {"message": "Success"}, 200
