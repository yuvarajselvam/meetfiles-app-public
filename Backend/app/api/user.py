import logging

from flask import Blueprint, request, redirect
from flask_login import current_user, logout_user

from app import app
from app.models.user import User


logger = logging.getLogger(__name__)
api = Blueprint('users', __name__, url_prefix='/api/v1/users')


def get_user(user_id):
    if not current_user.id == user_id:
        return {"Error": "Permission denied"}, 401
    user = User.find_one({"id": user_id})
    return user.json(), 200


def edit_user(user_id):
    if not current_user.id == user_id:
        return {"Error": "Permission denied"}, 401
    req_json = request.get_json()
    user = User.find_one({"id": user_id})
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
