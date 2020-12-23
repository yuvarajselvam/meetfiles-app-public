import json
import logging

from flask_login import current_user, logout_user
from flask import Blueprint, request, redirect, current_app

from app import app
from app.models.user import User
from app.models.meetsection import Meetsection


logger = logging.getLogger(__name__)
api = Blueprint('users', __name__, url_prefix='/api/v1/users')


def get_user(user_id):
    if user_id == "me":
        user_id = current_user.id
        with open(app.config.get('FIREBASE_OPTS_PATH')) as f:
            firebase = json.load(f)

    user = User.find_one({"id": user_id})
    if not user:
        return {"message": "User not found"}, 404
    to_ret = user.json()

    # TODO: Change accounts naming
    # As accounts can mean both meetfiles account and integration accounts

    to_ret.pop("primaryAccount", None)
    to_ret["account"] = to_ret.pop("accounts")[0]
    if firebase:
        to_ret["firebase"] = firebase

    to_ret["meetSections"] = []
    email = user.get_primary_email()
    meetsections = Meetsection.fetch_for_user(email)
    for meetsection in meetsections:
        m = {
            "id": meetsection["id"],
            "name": meetsection["name"],
            "members": meetsection["members"],
            "description": meetsection["description"]
        }
        if meetsection["createdBy"] == email:
            m["type"] = "self"
        elif meetsection["createdBy"] == "system":
            m["type"] = "default"
        else:
            m["type"] = "shared"
        to_ret["meetSections"].append(m)

    @current_app.after_response
    def post_process():
        user.sync_calendars()
    return to_ret, 200


def edit_user(user_id):
    if user_id == "me":
        user_id = current_user.id
    req_json = request.get_json()
    user = User.find_one({"id": user_id})
    if not user:
        return {"message": "User not found"}, 404
    for attribute in req_json:
        if hasattr(user, attribute):
            setattr(user, attribute, req_json[attribute])
        else:
            return {"Error": f"Invalid property `{attribute}` for User"}, 400
    user.save()
    return user.json(), 200


def sign_out():
    logout_user()
    redirect_url = app.config.get('APP_URL') + '/login'
    return redirect(redirect_url)


api.add_url_rule("/<user_id>/", view_func=get_user)
api.add_url_rule("/<user_id>/", methods=['PUT'], view_func=edit_user)
api.add_url_rule("/<user_id>/signout/", methods=['POST'], view_func=sign_out)
