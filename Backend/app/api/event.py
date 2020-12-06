import logging

from flask_login import current_user
from flask import Blueprint, request, jsonify

from app.models.event import Event
from app.models.meetsection import Meetsection
from app.models.followup import FollowUp

logger = logging.getLogger(__name__)
api = Blueprint('events', __name__, url_prefix='/api/v1/events')


def create_event():
    req_json = request.get_json()
    user = current_user
    account = user.get_account_by_email(req_json["email"])
    calendar = account.get_calendar()
    req_json.pop("id", None)
    req_json["user"] = user.id
    req_json["meetsection"] = req_json.pop("meetSection", None)
    req_json["attendees"] = [{"email": attendee} for attendee in req_json['attendees']]
    followup_event_id = req_json.pop("followUpEvent", None)
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
    Meetsection.bulk_update_firebase([m["id"] for m in event.meetsections])
    return jsonify(rv), 201


def get_event(event_id):
    query = {"id": event_id, "meetsections.user": current_user.id}
    event = Event.find_one(query=query)
    if not event:
        return {"message": "Event not found for user"}, 404
    return event.to_full_object(), 200


def edit_event(event_id):
    req_json = request.get_json()
    account = current_user.get_primary_account()
    query = {"id": event_id, "meetsections.user": current_user.id}
    event = Event.find_one(query=query)
    if not event:
        return {"message": "Event not found for user"}, 404
    if account.email != event.organizer:
        return {"message": "Permission denied"}, 403

    if event.recurrence:
        edit_type = req_json.pop("editType", None)
        if not edit_type:
            return {"message": "Trying to edit recurring event without `editType`"}, 400

    for attribute in req_json:
        if hasattr(event, attribute):
            if attribute == "attendees":
                attendees = []
                for attendee in req_json["attendees"]:
                    attendee.pop("type", None)
                    attendee.pop("displayName", None)
                    attendees.append(attendee)
                event.attendees = attendees
            else:
                setattr(event, attribute, req_json[attribute])
        else:
            raise AttributeError(f"Invalid property `{attribute}` for Event")

    calendar = account.get_calendar()
    calendar.edit_event(event, keys=req_json.keys())
    rv = event.json()
    Meetsection.bulk_update_firebase([m["id"] for m in event.meetsections])
    return jsonify(rv), 200


def rsvp_to_event(event_id):
    req_json = request.get_json()
    account = current_user.get_primary_account()
    query = {"id": event_id, "meetsections.user": current_user.id}
    event = Event.find_one(query=query)
    if not event:
        return {"message": "Event not found for user"}, 404

    calendar = account.get_calendar()
    calendar.rsvp_to_event(event, req_json["responseStatus"])
    rv = event.json()
    Meetsection.bulk_update_firebase([m["id"] for m in event.meetsections])
    return jsonify(rv), 200


api.add_url_rule('/', view_func=create_event, methods=['POST'])
api.add_url_rule('/<event_id>/', view_func=get_event)
api.add_url_rule('/<event_id>/', view_func=edit_event, methods=['PUT'])
