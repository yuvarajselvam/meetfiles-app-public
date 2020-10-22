import msal
import uuid
import logging

from flask_login import login_user
from flask import Blueprint, session, redirect

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import InvalidGrantError

from app import app
from app.utils.response import *
from app.models.user import User

logger = logging.getLogger(__name__)
api = Blueprint('signin', __name__, url_prefix='/api/v1/signin')

base_url = app.config.get('BASE_URL')
google_auth_base_url = "https://accounts.google.com/o/oauth2/auth"
google_client_id = app.config.get('GOOGLE_CLIENT_ID')
google_client_secret = app.config.get('GOOGLE_CLIENT_SECRET')
google_redirect_uri = base_url + '/api/v1/signin/google/callback/'
google_token_url = "https://accounts.google.com/o/oauth2/token"
google_scopes = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]
azure_client_id = app.config.get('AZURE_CLIENT_ID')
azure_client_secret = app.config.get('AZURE_CLIENT_SECRET')
azure_redirect_uri = base_url + '/api/v1/signin/azure/callback/'
azure_authority = "https://login.microsoftonline.com/common"
azure_scopes = ["User.ReadBasic.All"]


@api.route('/google/')
@precheck(subdomain=False)
def signin_with_google():
    google = OAuth2Session(google_client_id, scope=google_scopes, redirect_uri=google_redirect_uri)
    auth_url, state = google.authorization_url(google_auth_base_url,
                                               access_type="offline", prompt="select_account")
    session['oauth_state'] = state
    return redirect(auth_url)


@api.route('/google/callback/')
@precheck(required_fields=['code'], subdomain=False)
def signin_with_google_callback():
    if 'oauth_state' not in session:
        return {"message": "Session expired."}, 440
    google = OAuth2Session(google_client_id, redirect_uri=google_redirect_uri,
                           state=session['oauth_state'])
    try:
        token = google.fetch_token(google_token_url, client_secret=google_client_secret,
                                   code=request.args.get('code'))
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
            "phone": user_info.pop("phone", None)
        }
        user.add_account(google_object, user.primaryAccount)
    user.authenticate()
    login_user(user)
    if user.meetspaces:
        path = '/meetspaces'
    session['oauth_token'] = token
    redirect_url = app.config.get('APP_URL') + path
    return redirect(redirect_url)


def _build_msal_app():
    return msal.ConfidentialClientApplication(azure_client_id,
                                              client_credential=azure_client_secret,
                                              authority=azure_authority)


@api.route('/azure/')
@precheck(subdomain=False)
def signin_with_azure():
    state = str(uuid.uuid4())
    azure = _build_msal_app()
    auth_url = azure.get_authorization_request_url(azure_scopes, state=state,
                                                   redirect_uri=azure_redirect_uri)
    session['oauth_state'] = state
    return redirect(auth_url)


@api.route('/azure/callback/')
@precheck(required_fields=['code', 'state'], subdomain=False)
def signin_with_azure_callback():
    if request.args.get('state') != session.get("oauth_state"):
        return {"message": "Session expired."}, 440

    if "error" in request.args:
        return {"message": "Invalid Credentials."}, 401

    code = request.args.get('code')
    azure = _build_msal_app()
    result = azure.acquire_token_by_authorization_code(
        code, azure_scopes, redirect_uri=azure_redirect_uri)
    if "error" in result:
        return {"message": "Invalid Credentials."}, 401
    session["user"] = result.get("id_token_claims")
    accounts = azure.get_accounts()
    result = azure.acquire_token_silent(azure_scopes, account=accounts[0])
    return result
