import logging

from flask_login import current_user
from flask import Blueprint, request, jsonify

from app import app
from app.models.user import User
from app.extensions import mailer, firebase_service
from app.utils.precheck import precheck
from app.models.meetsection import Meetsection

logger = logging.getLogger(__name__)
api = Blueprint('meetsections', __name__, url_prefix='/api/v1/meetsections')


def send_invite(to_address, invitor):
    login_path = app.config.get('APP_URL') + '/login'
    sub = "You've been invited to Meetfiles!"
    msg = f'{invitor} is inviting you to their meetsection.\n' \
          f'Click <a href="{login_path}">here</a>.'
    mailer.send_message(to_address, sub, msg)


@precheck(required_fields=['name'])
def create_meetsection():
    request_json = request.get_json()
    current_user_json = current_user.get_primary_account().json()
    current_user_email = current_user_json["email"]
    meetsection_object = {
        "name": request_json.get('name'),
        "description": request_json.get('description'),
        "createdBy": current_user_email
    }
    meetsection = Meetsection(**meetsection_object)
    meetsection.add_user(current_user_email, owner=True)
    users = [current_user.id]
    for email in request_json.get('members', []):
        if not current_user_email == email:
            user = User.find_one({"accounts.email": email})
            if not user:
                send_invite(email, current_user_email)
            else:
                users.append(user.id)
            meetsection.add_user(email)
    try:
        meetsection.save()
    except (ValueError, AttributeError) as e:
        return {"message": str(e)}, 400
    firebase_service.notify_all(users, title="Meetsection created",
                                body=f"Meetsection {request_json.get('name')} successfully created")
    return meetsection.to_simple_object(), 201


def list_meetsections():
    meetsections = Meetsection.fetch_for_user(current_user.get_primary_email())
    current_user.sync_calendars()
    result = []
    for meetsection in meetsections:
        meetsection.pop('_id')
        result.append(Meetsection(**meetsection).to_full_object())
    return jsonify(result), 200


def get_meetsection(meetsection_id):
    query = {"id": meetsection_id, "members.email": current_user.get_primary_email()}
    meetsection = Meetsection.find_one(query=query)
    if not meetsection:
        return {"message": "Meetsection not found for user"}, 404
    return meetsection.to_full_object(), 200


def edit_meetsection(meetsection_id):
    query = {"id": meetsection_id, "members.email": current_user.get_primary_email()}
    req_json = request.get_json()
    meetsection = Meetsection.find_one(query=query)
    if not meetsection:
        return {"message": "Meetsection not found for user"}, 404
    for attribute in req_json:
        if hasattr(meetsection, attribute):
            setattr(meetsection, attribute, req_json[attribute])
        else:
            return {"message": f"Invalid property `{attribute}` for Meetsection"}, 400
    meetsection.save()
    return meetsection.to_simple_object(), 200


def add_user_to_meetsection(meetsection_id):
    user_emails = request.get_json()["emails"]
    current_user_email = current_user.get_primary_email()
    query = {"id": meetsection_id, "members.email": current_user_email}
    meetsection = Meetsection.find_one(query=query)
    if not meetsection:
        return {"message": "Meetsection not found for user"}, 404
    for email in user_emails:
        if not User.find_one({"accounts.email": email}):
            send_invite(email, current_user_email)
        meetsection.add_user(email)
    meetsection.save()
    return meetsection.to_simple_object(), 200


def remove_user_from_meetsection(meetsection_id):
    user_email = request.get_json()["email"]
    query = {"id": meetsection_id, "members.email": current_user.get_primary_email()}
    meetsection = Meetsection.find_one(query=query)
    if not meetsection:
        return {"message": "Meetsection not found for user"}, 404
    meetsection.remove_user(user_email)
    meetsection.save()
    return meetsection.to_simple_object(), 200


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
