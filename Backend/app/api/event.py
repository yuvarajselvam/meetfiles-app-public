import logging

from flask_login import current_user
from flask import Blueprint, request, jsonify

from app.models.event import Event
from app.models.followup import FollowUp

logger = logging.getLogger(__name__)
api = Blueprint('events', __name__, url_prefix='/api/v1/events')


def create_event():
    req_json = request.get_json()
    user = current_user
    if not user:
        return {"message": f"User `{req_json['email']}` does not exist"}, 400
    account = user.get_account_by_email(req_json["email"])
    calendar = account.get_calendar()
    req_json.pop("id", None)
    req_json["user"] = req_json.pop("email", None)
    req_json["meetsection"] = req_json.pop("meetSection", None)
    req_json["attendees"] = [{"email": attendee} for attendee in req_json['attendees']]
    followup_event_id = req_json.pop("followUpEventId", None)
    followup = None
    if followup_event_id:
        followup_event = Event.find_one(query={"id": followup_event_id})
        if not followup_event.followUp:
            followup = FollowUp(events=[followup_event.id])
            followup.save()
        else:
            followup = FollowUp.find_one({"id": followup_event.followUp})
    conf_type = req_json.pop("linkType", None)
    event = Event(**req_json)
    calendar.add_event(event, follow_up=followup, video_conf_type=conf_type)
    rv = event.json()
    return jsonify(rv), 201


def get_event(event_id):
    event = Event.find_one(query={"id": event_id})
    status_code = 200 if not event else 404
    return event.to_api_object(), status_code


def list_events_by_date_range():
    start = request.args.get("start")
    end = request.args.get("end")
    result = Event.fetch_by_date_range(start, end)
    status_code = 200 if result else 204
    return jsonify(result), status_code


def is_conflict():
    start = request.args.get("start")
    end = request.args.get("end")
    result = Event.fetch_by_date_range(start, end)
    return {"eventsCount": len(result)}, 200


api.add_url_rule('/', view_func=create_event, methods=['POST'])
api.add_url_rule('/', view_func=list_events_by_date_range)
api.add_url_rule('/<event_id>/', view_func=get_event)
api.add_url_rule('/conflict/', view_func=is_conflict)
