import msal
import logging

from flask_login import login_user
from flask import Blueprint, session, redirect, request

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import InvalidGrantError

from app import app
from app.models.user import User
from app.models.event import Event
from app.utils.response import precheck

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
azure_auth_base = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
azure_client_id = app.config.get('AZURE_CLIENT_ID')
azure_client_secret = app.config.get('AZURE_CLIENT_SECRET')
azure_redirect_uri = 'http://localhost:5000' + '/api/v1/signin/azure/callback/'
azure_token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
azure_scopes = ["Calendars.ReadWrite", "User.ReadBasic.All"]


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
    logger.debug(f"User logging in - {user_info['email']}")
    user = User.find_one({"accounts.google.email": user_info["email"]})
    path = '/get-started/create'
    if not user:
        user_object = {
            "id": "USR" + user_info["id"],
            "primaryAccount": User.Account.Type.GOOGLE.value,
        }
        user = User(user_object)
        google_object = {
            "name": user_info["name"],
            "email": user_info["email"],
            "imageUrl": user_info.pop("picture", None),
            "phone": user_info.pop("phone", None),
            "refreshToken": token['refresh_token']
        }
        user.add_account(google_object, user.primaryAccount)
    user.authenticate()
    login_user(user)
    google = user.get_primary_account()
    events = google.fetch_google_calendar_events()
    print(Event.sync_google_events(events, 'yuvi', "yuvi's meetsection", google.email))
    user.accounts["google"] = google.json()
    user.save()
    if user.meetspaces:
        path = '/meetspaces'
    session['oauth_token'] = token
    redirect_url = app.config.get('APP_URL') + path
    return redirect(redirect_url)


def signin_with_azure():
    azure = OAuth2Session(azure_client_id, scope=azure_scopes, redirect_uri=azure_redirect_uri)
    auth_url, state = azure.authorization_url(azure_auth_base, access_type="offline", prompt="select_account")
    print(auth_url)
    session['oauth_state'] = state
    return redirect(auth_url)


@precheck(required_fields=['code'])
def signin_with_azure_callback():
    if app.config.get('FLASK_ENV') == "dev":
        if app.config.get('SESSION_COOKIE_DOMAIN') not in request.url:
            return redirect(base_url + request.full_path)

    azure = OAuth2Session(azure_client_id, redirect_uri=azure_redirect_uri, state=session['oauth_state'])
    try:
        code = request.args.get('code')
        token = azure.fetch_token(azure_token_url, client_secret=azure_client_secret, code=code)
    except InvalidGrantError:
        return {"message": "Invalid Credentials."}, 401
    return token


api.add_url_rule('/google/', view_func=signin_with_google)
api.add_url_rule('/google/callback/', view_func=signin_with_google_callback)
api.add_url_rule('/azure/', view_func=signin_with_azure)
api.add_url_rule('/azure/callback/', view_func=signin_with_azure_callback)
