import logging

from enum import Enum

import requests

from requests_oauthlib import OAuth2Session
from google.oauth2.credentials import Credentials as GoogleCredentials

from app import app
from app.utils import validation
from app.models.calendar import Calendar
from app.models.base.entity import EntityBase

logger = logging.getLogger(__name__)


class Account(EntityBase):
    _required_fields = ["email", "name"]

    def __init__(self,
                 name: str = None,
                 type: str = None,
                 email: str = None,
                 imageUrl: str = None,
                 providerId: str = None,
                 accessToken: str = None,
                 refreshToken: str = None,
                 *args, **kwargs):
        self._user = None
        self.name = name
        self._type = type
        self.email = email
        self.imageUrl = imageUrl
        self.providerId = providerId
        self.accessToken = accessToken
        self.refreshToken = refreshToken

    def get_user_id(self):
        return self._user.id

    def get_user(self):
        return self._user

    def update_token(self, token):
        self.accessToken = token.get("access_token")
        self.refreshToken = token.get("refresh_token")
        [d.update(self.json()) for d in self._user.accounts if d["type"] == self.type]

    def get_calendar(self):
        calendar = Calendar.find_one(query={"user": self.email, "provider": self._type})
        if not calendar:
            calendar = Calendar(user=self.email, provider=self._type)
        calendar._account = self
        return calendar

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        display_name = "Name"
        validation.check_min_length(display_name, value, 1)
        self._name = value

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        self._type = value

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, value):
        display_name = "Email"
        validation.check_regex_match(display_name, value, validation.EMAIL_REGEX)
        self._email = value

    @property
    def imageUrl(self):
        return self._image_url

    @imageUrl.setter
    def imageUrl(self, value):
        validation.check_regex_match("Image URL", value, validation.URL_REGEX)
        self._image_url = value

    @property
    def providerId(self):
        return self._provider_id

    @providerId.setter
    def providerId(self, value):
        self._provider_id = value

    @property
    def accessToken(self):
        return self._access_token

    @accessToken.setter
    def accessToken(self, value):
        self._access_token = value

    @property
    def refreshToken(self):
        return self._refresh_token

    @refreshToken.setter
    def refreshToken(self, value):
        self._refresh_token = value

    # Enums

    # <editor-fold desc="Account Type Enum">
    class Type(Enum):
        GOOGLE = 'google'
        MICROSOFT = 'microsoft'
    # </editor-fold>


class Google(Account):
    _token_uri = 'https://accounts.google.com/o/oauth2/token'
    _scopes = ["https://www.googleapis.com/auth/userinfo.email",
               "https://www.googleapis.com/auth/userinfo.profile",
               'https://www.googleapis.com/auth/calendar']
    _client_id = app.config.get('GOOGLE_CLIENT_ID')
    _client_secret = app.config.get('GOOGLE_CLIENT_SECRET')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = self.Type.GOOGLE.value.lower()

    def get_credentials(self):
        google = self

        class Credentials(GoogleCredentials):
            def refresh(self, request):
                super().refresh(request)
                token = {"access_token": self.token, "refresh_token": self._refresh_token}
                google.update_token(token)

        auth_user_info = {
            'token_uri': self._token_uri,
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            'refresh_token': self._refresh_token,
            'scopes': self._scopes
        }
        return Credentials.from_authorized_user_info(auth_user_info)


class Microsoft(Account):
    _token_uri = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
    _scopes = ["Calendars.ReadWrite", "User.Read.All", "openid", "email", "offline_access"]
    _client_id = app.config.get('MICROSOFT_CLIENT_ID')
    _client_secret = app.config.get('MICROSOFT_CLIENT_SECRET')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = self.Type.MICROSOFT.value.lower()
        self._service = None

    def get_service(self):
        if not self._service:
            creds = {
                "access_token": self.accessToken,
                "refresh_token": self.refreshToken,
                "token_type": "Bearer"
            }
            extra = {"client_id": self._client_id, "client_secret": self._client_secret}
            self._service = self.OAuthSession(self._client_id, token_updater=self.update_token,
                                              auto_refresh_kwargs=extra, token=creds,
                                              auto_refresh_url=self._token_uri)
        return self._service

    def fetch_event_attachments(self, event_id):
        service = self.get_service()
        graph_url = 'https://graph.microsoft.com/v1.0'
        return service.get(f"{graph_url}/me/events/{event_id}/attachments").json()

    class OAuthSession(OAuth2Session):
        def refresh_token(self, url, *args, **kwargs):
            data = {
                'client_id': self.auto_refresh_kwargs.get('client_id'),
                'client_secret': self.auto_refresh_kwargs.get('client_secret'),
                'grant_type': 'refresh_token',
                'refresh_token': self.token.get("refresh_token")
            }
            response = requests.post(url, data=data)
            token = response.json()
            token.pop('expires_in')
            if "refresh_token" not in token:
                token["refresh_token"] = self.token.get("refresh_token")
            self.token = token
            self.token_updater(token)

        def request(self, method, url, data=None, headers=None, **kwargs):
            result = super().request(method, url, data=None, headers=None, **kwargs)
            error = result.json().get('error')
            if isinstance(error, dict) and (error.get('code') == "InvalidAuthenticationToken"):
                self.refresh_token(self.auto_refresh_url)
                result = super().request(method, url, data=None, headers=None, **kwargs)
            return result
