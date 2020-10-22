import logging

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from app.utils.response import *
from app.models.user import User
from app.models.meetspace import Meetspace
from app.models.meetsection import Meetsection

from app.extensions import db


logger = logging.getLogger(__name__)
api = Blueprint('meetspace', __name__, url_prefix='/api/v1')


@api.route('/meetspace/is_unique/')
@precheck(required_fields=['q'])
@login_required
def is_meetspace_name_unique():
    query = request.args.get("q")
    is_unique = Meetspace.find_one({'name': query}) is None
    return {"isUnique": str(is_unique)}, 200


@api.route('/meetspace/', methods=['POST'])
@precheck(required_fields=['name'])
@login_required
def create_meetspace():
    request_json = request.get_json()
    current_user_json = current_user.get_primary_account().json()
    current_user_email = current_user_json["email"]

    if Meetspace.find_one({'name': request_json.get('name')}):
        return {"Error": f"Meetspace: {request_json.get('name')} already exists!"}, 409

    meetspace_object = {
        "name": request_json.get("name"),
        "owners": [current_user_email],
        "createdBy": current_user_email
    }
    meetsection_object = {
        "name": Meetsection.get_default_name(current_user_json['name']),
        "members": [current_user_email],
        "meetspace": meetspace_object['name'],
        "description": Meetsection.get_default_desc(),
        "createdBy": current_user_email
    }

    try:
        with db.get_session() as session:
            meetspace = Meetspace(meetspace_object)
            meetspace.save(session=session)
            meetsection = Meetsection(meetsection_object)
            meetsection.save(session=session)
    except (ValueError, AttributeError) as e:
        return {"Error": str(e)}, 400

    current_user.add_meetspace(meetspace_object['name'], User.Role.OWNER)
    rv = {"meetspace": meetspace.json(), "meetsection": meetsection.json()}
    return rv, 201


@api.route('/meta/')
@login_required
def get_meetspace():
    subdomain = request.subdomain
    meetspace = Meetspace.find_one({'name': subdomain})
    if not meetspace:
        return {"Error": f"Meetspace: {subdomain} not found."}, 404
    return meetspace.json()


@api.route('/meetspaces/')
@login_required
def get_all_meetspaces():
    user_json = current_user.json()
    meetspaces = []
    if 'meetspaces' not in user_json:
        return jsonify(meetspaces), 204
    for meetspace_name in user_json['meetspaces'].keys():
        meetspace = Meetspace.find_one({"name": meetspace_name})
        meetspaces.append(meetspace.json())
    return meetspaces, 200
