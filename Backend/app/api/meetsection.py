import logging

from flask_login import current_user
from flask import Blueprint, request, jsonify

from app.utils.precheck import precheck
from app.models.meetsection import Meetsection

logger = logging.getLogger(__name__)
api = Blueprint('meetsections', __name__, url_prefix='/api/v1/meetsections')


@precheck(required_fields=['name'])
def create_meetsection():
    request_json = request.get_json()
    current_user_json = current_user.get_primary_account().json()
    current_user_email = current_user_json["email"]
    members = request_json.get('members') or []
    if current_user_email not in members:
        members.append(current_user_email)

    meetsection_object = {
        "name": request_json.get('name'),
        "members": members,
        "meetspace": request.subdomain,
        "description": request_json.get('description'),
        "createdBy": current_user_email
    }

    try:
        meetsection = Meetsection(**meetsection_object)
        meetsection.save()
    except (ValueError, AttributeError) as e:
        return {"Error": str(e)}, 400

    return meetsection.json(), 201


def list_meetsections():
    meetsections = Meetsection.fetch_for_user(current_user.get_primary_email())
    return jsonify(meetsections), 200


api.add_url_rule('/', methods=['POST'], view_func=create_meetsection)
api.add_url_rule('/', methods=['GET'], view_func=list_meetsections)
