import json
import base64
import logging

from flask_login import login_user
from flask import Blueprint, session, redirect, request

import requests
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import InvalidGrantError

from app import app
from app.models.user import User
from app.utils.precheck import precheck
from app.models.base.account import Account

logger = logging.getLogger(__name__)
api = Blueprint('signin', __name__, url_prefix='/api/v1/signin')

base_url = app.config.get('BASE_URL')
google_auth_base = "https://accounts.google.com/o/oauth2/auth"
google_client_id = app.config.get('GOOGLE_CLIENT_ID')
google_client_secret = app.config.get('GOOGLE_CLIENT_SECRET')
google_redirect_uri = base_url + '/api/v1/signin/google/callback/'
google_token_url = "https://accounts.google.com/o/oauth2/token"
google_scopes = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    'https://www.googleapis.com/auth/calendar'
]
microsoft_auth_base = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
microsoft_client_id = app.config.get('MICROSOFT_CLIENT_ID')
microsoft_client_secret = app.config.get('MICROSOFT_CLIENT_SECRET')
microsoft_redirect_uri = 'http://localhost:5000' + '/api/v1/signin/microsoft/callback/'
microsoft_token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
microsoft_scopes = ["Calendars.ReadWrite", "User.Read.All", "openid", "email", "offline_access"]


def signin_with_google():
    google = OAuth2Session(google_client_id, scope=google_scopes, redirect_uri=google_redirect_uri)
    auth_url, state = google.authorization_url(google_auth_base,
                                               access_type="offline", prompt="select_account")
    session['oauth_state'] = state
    return redirect(auth_url)


@precheck(required_fields=['code'])
def signin_with_google_callback():
    if 'oauth_state' not in session:
        return {"message": "Session expired."}, 440
    google = OAuth2Session(google_client_id, redirect_uri=google_redirect_uri, state=session['oauth_state'])
    try:
        code = request.args.get('code')
        token = google.fetch_token(google_token_url, client_secret=google_client_secret, code=code)
    except InvalidGrantError:
        return {"message": "Invalid Credentials."}, 401
    user_info = google.get('https://www.googleapis.com/oauth2/v1/userinfo').json()
    user = User.find_one({"accounts.email": user_info['email'], "accounts.type": "google"})
    path = '/get-started/create'
    initial = False
    if not user:
        initial = True
        user_object = {"primaryAccount": Account.Type.GOOGLE.value}
        user = User(**user_object)
        google_object = {
            "providerId": "USR" + user_info["id"],
            "name": user_info["name"],
            "email": user_info["email"],
            "imageUrl": user_info.pop("picture", None),
            "phone": user_info.pop("phone", None),
            "accessToken": token['access_token'],
            "refreshToken": token['refresh_token']
        }
        user.add_account(google_object, user.primaryAccount)
    user.authenticate()
    login_user(user)
    user.sync_calendars(initial=initial)
    if user.meetspaces:
        path = '/meetspaces'
    session['oauth_token'] = token
    redirect_url = app.config.get('APP_URL') + path
    return redirect(redirect_url)


def signin_with_microsoft():
    microsoft = OAuth2Session(microsoft_client_id, scope=microsoft_scopes, redirect_uri=microsoft_redirect_uri)
    auth_url, state = microsoft.authorization_url(microsoft_auth_base, access_type="offline", prompt="select_account")
    session['oauth_state'] = state
    return redirect(auth_url)


@precheck(required_fields=['code'])
def signin_with_microsoft_callback():
    microsoft = OAuth2Session(microsoft_client_id, redirect_uri=microsoft_redirect_uri, state=session['oauth_state'])
    try:
        code = request.args.get('code')
        token = microsoft.fetch_token(microsoft_token_url, client_secret=microsoft_client_secret, code=code)
    except InvalidGrantError:
        return {"message": "Invalid Credentials."}, 401

    email = _decode_id_token(token['id_token']).get('email')
    if not email:
        return {"message": "No email address is associated with this account."}

    user_info = microsoft.get('https://graph.microsoft.com/v1.0/me').json()
    user = User.find_one({"accounts.email": email, "accounts.type": "microsoft"})
    path = '/get-started/create'
    initial = False
    if not user:
        initial = True
        user_object = {"primaryAccount": Account.Type.MICROSOFT.value}
        user = User(**user_object)
        microsoft_object = {
            "providerId": "USR" + user_info["id"],
            "name": user_info["displayName"],
            "email": email,
            "imageUrl": user_info.pop("picture", None),
            "phone": user_info.pop("phone", None),
            "accessToken": token['access_token'],
            "refreshToken": token['refresh_token']
        }
        user.add_account(microsoft_object, user.primaryAccount)
    user.authenticate()
    login_user(user)
    if user.meetspaces:
        path = '/meetspaces'
    user.sync_calendars(initial=initial)
    session['oauth_token'] = token
    redirect_url = app.config.get('APP_URL') + path
    return redirect(redirect_url)


def zoom_callback():
    zoom_client_id = "***REMOVED***"
    zoom_client_secret = "***REMOVED***"
    zoom_token_url = "https://zoom.us/oauth/token"
    params = {
        "grant_type": "authorization_code",
        "code": request.args.get('code'),
        "redirect_uri": "https://7a43c7f7a31d.ngrok.io/api/v1/signin/zoom/callback/"
    }
    auth = HTTPBasicAuth(zoom_client_id, zoom_client_secret)
    try:
        token = requests.post(zoom_token_url, params=params, auth=auth)
    except InvalidGrantError:
        return {"message": "Invalid Credentials."}, 401
    return redirect(app.config.get('APP_URL'))


def _decode_id_token(id_token):
    id_token = id_token.split('.')[1] + "==="
    a = json.loads(base64.urlsafe_b64decode(id_token))
    return a


api.add_url_rule('/google/', view_func=signin_with_google)
api.add_url_rule('/google/callback/', view_func=signin_with_google_callback)
api.add_url_rule('/microsoft/', view_func=signin_with_microsoft)
api.add_url_rule('/microsoft/callback/', view_func=signin_with_microsoft_callback)
api.add_url_rule('/zoom/callback/', view_func=zoom_callback)
