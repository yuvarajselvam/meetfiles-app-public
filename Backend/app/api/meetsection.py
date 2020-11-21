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
    members = request_json.get('members') or [{"email": current_user_email,
                                               "role": Meetsection.Role.OWNER.value}]
    if not next((i for i, member in enumerate(members) if member["email"] == current_user_email), None):
        members.append({"email": current_user_email, "role": Meetsection.Role.OWNER.value})
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
        return {"message": str(e)}, 400

    return meetsection.json(), 201


def list_meetsections():
    meetsections = Meetsection.fetch_for_user(current_user.get_primary_email())
    result = []
    for meetsection in meetsections:
        meetsection.pop('_id')
        result.append(Meetsection(**meetsection).json(deep=True))
    return jsonify(result), 200


def get_meetsection(meetsection_id):
    meetsection = Meetsection.find_one(query={"id": meetsection_id})
    status_code = 200 if not meetsection else 404
    return meetsection.json(deep=True), status_code


def edit_meetsection(meetsection_id):
    req_json = request.get_json()
    meetsection = Meetsection.find_one({"id": meetsection_id, "members": current_user.get_primary_email()})
    if not meetsection:
        return {"message": "Meetsection not found for user"}, 404
    for attribute in req_json:
        if hasattr(meetsection, attribute):
            setattr(meetsection, attribute, req_json[attribute])
        else:
            return {"message": f"Invalid property `{attribute}` for Meetsection"}, 400
    meetsection.save()
    return meetsection.json(), 200


def add_user_to_meetsection(meetsection_id):
    user_email = request.get_json()["email"]
    meetsection = Meetsection.find_one({"id": meetsection_id, "members": current_user.get_primary_email()})
    if not meetsection:
        return {"message": "Meetsection not found for user"}, 404
    meetsection.add_user(user_email)
    meetsection.save()
    return meetsection.json(), 200


def remove_user_from_meetsection(meetsection_id):
    user_email = request.get_json()["email"]
    meetsection = Meetsection.find_one({"id": meetsection_id, "members": current_user.get_primary_email()})
    if not meetsection:
        return {"message": "Meetsection not found for user"}, 404
    meetsection.remove_user(user_email)
    meetsection.save()
    return meetsection.json(), 200


def is_meetsection_name_unique():
    query = request.args.get("q")
    account = current_user.get_primary_account()
    is_unique = Meetsection.find_one({'name': query, "members.email": account.email}) is None
    is_unique = is_unique and not query == Meetsection.get_default_name(account.name)
    return {"isUnique": str(is_unique)}, 200


api.add_url_rule('/', view_func=list_meetsections)
api.add_url_rule('/<meetsection_id>/', view_func=get_meetsection)
api.add_url_rule('/', methods=['POST'], view_func=create_meetsection)
api.add_url_rule('/<meetsection_id>/', methods=['PUT'], view_func=edit_meetsection)
api.add_url_rule('/<meetsection_id>/users/', methods=['POST'], view_func=add_user_to_meetsection)
api.add_url_rule('/<meetsection_id>/users/', methods=['DELETE'], view_func=remove_user_from_meetsection)
api.add_url_rule('/is_unique/', view_func=is_meetsection_name_unique)
