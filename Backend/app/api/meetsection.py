import logging

from flask import Blueprint, request
from flask_login import login_required, current_user

from app.models.meetsection import Meetsection

logger = logging.getLogger(__name__)
api = Blueprint('meetsection', __name__, url_prefix='/api/v1')


@api.route('/meetsection', methods=['POST'])
@login_required
def create_meetsection():
    request_json = request.get_json()
    current_user_json = current_user.get_primary_account().json()
    current_user_email = current_user_json["email"]
    members = set(request_json.get('members'))
    members.add(current_user_email)

    meetsection_object = {
        "name": request_json.get('name'),
        "members": members,
        "meetspace": request.subdomain,
        "description": request_json.get('description'),
        "createdBy": current_user_email
    }

    try:
        meetsection = Meetsection(meetsection_object)
        meetsection.save()
    except (ValueError, AttributeError) as e:
        return {"Error": str(e)}, 400

    return meetsection.json(), 201
