import logging

from flask import Blueprint, request

from app.models.user import User
from app.models.event import Event

logger = logging.getLogger(__name__)
api = Blueprint('events', __name__, url_prefix='/api/v1/events')


def create_event():
    req_json = request.get_json()
    user = User.find_one({"accounts.email": req_json["email"]})
    account = user.get_account_by_email(req_json["email"])
    calendar = account.get_calendar()
    event = Event()
    calendar.add_event(event)
