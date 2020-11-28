import json
import logging

from flask import Blueprint, request, redirect
from flask_login import current_user, logout_user

from app import app
from app.models.user import User


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
    obj = user.json()
    # TODO: Change accounts naming
    # As accounts can mean both meetfiles account and integration accounts
    del obj["primaryAccount"]
    obj["account"] = obj.pop("accounts")[0]
    if firebase:
        obj["firebase"] = firebase
    return obj, 200


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
