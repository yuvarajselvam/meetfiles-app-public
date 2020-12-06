import logging

from flask_login import current_user
from flask import Blueprint, jsonify, request

from app.models.event import Event

logger = logging.getLogger(__name__)
api = Blueprint('calendars', __name__, url_prefix='/api/v1/calendars')


def list_events_by_date_range():
    start = request.args.get("start")
    end = request.args.get("end")
    result = Event.fetch_by_date_range(start, end, current_user.id, calendar=True)
    status_code = 200 if result else 204
    return jsonify(result), status_code


api.add_url_rule('/events/', view_func=list_events_by_date_range)
