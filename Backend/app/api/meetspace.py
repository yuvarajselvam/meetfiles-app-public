import logging

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from app.models.user import User
from app.models.meetspace import Meetspace as Meetspace

logger = logging.getLogger(__name__)
api = Blueprint('meetspace', __name__, url_prefix='/api/v1')


@api.route('/meetspace/')
@login_required
def post():
    request_json = request.get_json()
    current_user_email = current_user.get_primary_email()
    meetspace_object = {
        "name": request_json.get("name"),
        "owners": [current_user_email],
        "createdBy": [current_user_email]
    }
    meetspace = Meetspace(meetspace_object)
    meetspace.save()
    current_user.add_meetspace(meetspace_object['name'], User.Role.OWNER)
    return meetspace.json(), 201


@api.route('/meetspaces/')
@login_required
def get():
    user_json = current_user.json()
    print(user_json)
    meetspaces = []
    if 'meetspaces' not in user_json:
        return jsonify(meetspaces), 204
    for meetspace_name in user_json['meetspaces'].keys():
        meetspace = Meetspace.find_one({"name": meetspace_name})
        meetspaces.append(meetspace.json())
    return meetspaces, 200


