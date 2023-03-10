import logging
from datetime import datetime

from flask_login import current_user
from flask import Blueprint, request, jsonify, current_app

from app.models.user import User
from app.models.followup import FollowUp
from app.models.event import Event, RecurringExceptionEvent as REE

logger = logging.getLogger(__name__)
api = Blueprint('events', __name__, url_prefix='/api/v1/events')


def create_event():
    req_json = request.get_json()
    print(req_json)
    account = current_user.get_account_by_email(req_json["email"])
    calendar = account.get_calendar()
    req_json.pop("id", None)
    if "meetsection" in req_json:
        req_json["meetsections"] = [req_json.pop("meetsection")]
    req_json["user"] = current_user.id
    req_json["attendees"] = [{"email": attendee["email"]} for attendee in req_json['attendees']]
    rr = req_json.pop("recurrence", None)
    if rr:
        req_json["recurrence"] = [rule for rule in str(rr).split('\n')
                                  if not rule.startswith('DTSTART')]
        req_json["isRecurring"] = True
    followup_event_id = req_json.pop("followUpEvent", None)
    followup = None
    if followup_event_id:
        followup_event = Event.find_one(query={"id": followup_event_id})
        req_json["meetsections"] = followup_event.meetsections
        if not followup_event.followUp:
            followup = FollowUp(events=[followup_event.id])
            followup.save()
        else:
            followup = FollowUp.find_one({"id": followup_event.followUp})
    conf_type = req_json.pop("linkType", None)
    event = Event(**req_json)
    calendar.add_event(event, follow_up=followup, video_conf_type=conf_type)
    rv = event.to_full_object(current_user.id, current_user.timeZone)
    user_id = current_user.id

    @current_app.after_response
    def post_process():
        User.find_one({"id": user_id}).sync_calendars()
    return jsonify(rv), 201


def get_event(event_id):
    query = {"id": event_id.split('__')[0], "user": current_user.id}
    event = Event.find_one(query=query)
    if not event:
        return {"message": "Event not found for user"}, 404
    return event.to_full_object(current_user.id, timezone=current_user.timeZone), 200


def edit_event(event_id):
    req_json = request.get_json()
    account = current_user.get_primary_account()
    query = {"id": event_id.split('__')[0], "user": current_user.id}
    event = Event.find_one(query=query)
    if not event:
        return {"message": "Event not found for user"}, 404
    if account.email != event.organizer:
        return {"message": "Permission denied"}, 403

    edit_type = req_json.pop("editType", None)
    if not edit_type and event.isRecurring:
        edit_type = 'THIS'
        # return {"message": "Trying to edit recurring event without `editType`"}, 400
    instance_id = event_id if event.isRecurring else None

    duration = event.end - event.start
    original_start = datetime.strptime(instance_id.split('__')[1], '%Y%m%dT%H%M%SZ')
    original_end = original_start + duration
    if "start" not in req_json:
        event.start = original_start
    if "end" not in req_json:
        event.end = original_end

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

    if not event.end > event.start:
        return {"message": "End should be later than start of the event"}, 400

    calendar = account.get_calendar()
    calendar.edit_event(event, edit_type=edit_type, instance_id=instance_id, keys=req_json.keys())
    rv = event.to_full_object(current_user.id, current_user.timeZone)
    user_id = current_user.id

    @current_app.after_response
    def post_process():
        User.find_one({"id": user_id}).sync_calendars()
    return jsonify(rv), 200


def rsvp_to_event(event_id):
    req_json = request.get_json()
    account = current_user.get_primary_account()
    if "__" in event_id:
        event_id = event_id.split('__')[0]
    query = {"id": event_id, "user": current_user.id}
    event = Event.find_one(query=query)
    if not event:
        return {"message": "Event not found for user"}, 404

    calendar = account.get_calendar()
    calendar.rsvp_to_event(event, req_json["responseStatus"])
    rv = event.json()
    user_id = current_user.id

    @current_app.after_response
    def post_process():
        User.find_one({"id": user_id}).sync_calendars()
    return jsonify(rv), 200


def delete_event(event_id):
    account = current_user.get_primary_account()
    e = event_id
    if "__" in event_id:
        e = event_id.split('__')[0]
    query = {"id": e, "user": current_user.id}
    event = Event.find_one(query=query)
    if not event:
        return {"message": "Event not found for user"}, 404
    if account.email != event.organizer:
        return {"message": "Permission denied"}, 403

    delete_type = request.args.get("deleteType", None)
    if not delete_type and event.isRecurring:
        delete_type = 'THIS'
        # return {"message": "Trying to delete recurring event without `deleteType`"}, 400
    instance_id = event_id if event.isRecurring else None

    calendar = account.get_calendar()
    calendar.delete_event(event, delete_type=delete_type, instance_id=instance_id)
    user_id = current_user.id

    @current_app.after_response
    def post_process():
        User.find_one({"id": user_id}).sync_calendars()
    return {}, 200


# def move_event(event_id):
#     req_json = request.get_json()
#     if "__" in event_id:
#         event_id = event_id.split('__')[0]
#     query = {"id": event_id, "user": current_user.id}
#     event = Event.find_one(query=query)
#     if not event:
#         return {"message": "Event not found for user"}, 404
#
#     meetsections = event.meetsections
#     for m in meetsections:
#         if m["user"] == current_user.id:
#             m["id"] = req_json["meetSection"]
#     print(event.meetsections)
#     event.meetsections = meetsections
#     event.save()
#     return {"message": "success"}, 200


def conflicts():
    start = request.args.get("start")
    end = request.args.get("end")
    result = Event.fetch_by_date_range(start, end, current_user.id)
    return {"count": len(result)}, 200


def search():
    q = request.args.get("q")
    meetsection = request.args.get("meetSection")
    if not q:
        return {"message": "Search term `q` cannot be empty."}
    query = {"$text": {"$search": q.strip()}, "user": current_user.id}
    if meetsection:
        query["meetsections"] = meetsection
    results = [Event(**e).to_simple_object() for e in Event.find(query)] + \
              [REE(**ree).to_simple_object() for ree in REE.find(query)]
    status_code = 200 if results else 204
    return jsonify(results), status_code


api.add_url_rule('/', view_func=create_event, methods=['POST'])
api.add_url_rule('/<event_id>/', view_func=get_event)
api.add_url_rule('/<event_id>/', view_func=edit_event, methods=['PUT'])
api.add_url_rule('/<event_id>/', view_func=delete_event, methods=['DELETE'])
api.add_url_rule('/conflicts/', view_func=conflicts)
api.add_url_rule('/search/', view_func=search)
