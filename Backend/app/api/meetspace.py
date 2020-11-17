import logging

from flask_login import current_user
from flask import Blueprint, jsonify, request

from app.extensions import db
from app.utils.precheck import precheck
from app.models.user import User
from app.models.meetsection import Meetsection
from app.models.meetspace import Meetspace

logger = logging.getLogger(__name__)
api = Blueprint('meetspace', __name__, url_prefix='/api/v1')

RESERVED_SUBDOMAINS = ['app', 'api', 'docs', 'logs', 'status', 'config', 'dev']


@precheck(required_fields=['q'])
def is_meetspace_name_unique():
    query = request.args.get("q")
    is_unique = Meetspace.find_one({'name': query}) is None
    return {"isUnique": str(is_unique)}, 200


@precheck(required_fields=['name'])
def create_meetspace():
    request_json = request.get_json()
    current_user_json = current_user.get_primary_account().json()
    current_user_email = current_user_json["email"]
    meetspace_name = request_json.get('name')
    if Meetspace.find_one({'name': meetspace_name}) or meetspace_name in RESERVED_SUBDOMAINS:
        return {"Error": f"Meetspace: `{meetspace_name}` already exists!"}, 409

    if meetspace_name.contains('.'):
        return {"Error": f"Meetspace name cannot contain a `.` (dot)."}, 400

    meetspace_object = {
        "name": meetspace_name,
        "owners": [current_user_email],
        "createdBy": current_user_email
    }
    meetsection_object = {
        "name": Meetsection.get_default_name(current_user_json['name']),
        "members": [current_user_email],
        "meetspace": meetspace_object['name'],
        "description": Meetsection.get_personal_desc(),
        "createdBy": current_user_email
    }

    try:
        with db.get_session() as session:
            with session.start_transaction():
                meetspace = Meetspace(**meetspace_object)
                meetspace.save(session=session)
                meetsection = Meetsection(**meetsection_object)
                meetsection.save(session=session)
    except (ValueError, AttributeError) as e:
        return {"Error": str(e)}, 400

    current_user.add_meetspace(meetspace_object['name'], User.Role.OWNER)
    rv = {"meetspace": meetspace.json(), "meetsection": meetsection.json()}
    return rv, 201


def get_meetspace_meta():
    subdomain = request.subdomain
    meetspace = Meetspace.find_one({'name': subdomain})
    if not meetspace:
        return {"Error": f"Meetspace: `{subdomain}` not found."}, 404
    return meetspace.json()


def get_all_meetspaces():
    user_json = current_user.json()
    meetspaces = []
    if 'meetspaces' not in user_json:
        return jsonify(meetspaces), 204
    for meetspace_name in user_json['meetspaces'].keys():
        meetspace = Meetspace.find_one({"name": meetspace_name})
        meetspaces.append(meetspace.json())
    return meetspaces, 200


api.add_url_rule('/meetspace/is_unique/', view_func=is_meetspace_name_unique)
api.add_url_rule('/meetspace/', methods=['POST'], view_func=create_meetspace)
api.add_url_rule('/meta/', view_func=get_meetspace_meta)
api.add_url_rule('/meetspaces/', view_func=get_all_meetspaces)
