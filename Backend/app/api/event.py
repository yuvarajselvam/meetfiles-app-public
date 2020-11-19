import logging

from flask_login import current_user
from flask import Blueprint, request, jsonify

from app.models.event import Event

logger = logging.getLogger(__name__)
api = Blueprint('events', __name__, url_prefix='/api/v1/events')


def create_event():
    req_json = request.get_json()
    user = current_user
    if not user:
        return {"message": f"User `{req_json['email']}` does not exist"}, 400
    account = user.get_account_by_email(req_json["email"])
    calendar = account.get_calendar()
    req_json["user"] = req_json.pop("email", None)
    req_json["meetsection"] = req_json.pop("meetSection", None)
    conf_type = req_json.pop("linkType")
    attendees = []
    for attendee in req_json['attendees']:
        attendees.append({"email": attendee})
    req_json["attendees"] = attendees
    event = Event(**req_json)
    calendar.add_event(event, video_conf_type=conf_type)
    rv = event.json()
    return jsonify(rv), 201


api.add_url_rule('/', view_func=create_event, methods=['POST'])
