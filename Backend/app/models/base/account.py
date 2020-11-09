import logging

from enum import Enum
from urllib import parse
from datetime import datetime

import requests

from requests_oauthlib import OAuth2Session
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError as GoogleHttpError
from google.oauth2.credentials import Credentials as GoogleCredentials

from app import app
from app.utils import validation
from app.models.base.entity import EntityBase

logger = logging.getLogger(__name__)


class Account(EntityBase):
    _required_fields = ["email", "name"]

    CALENDAR_MAX_END = "2050-12-31 23:59:59.999Z"

    _type = ''
    _user = None
    _name = _email = _image_url = _provider_id = \
        _access_token = _refresh_token = _calendar_sync_token = None

    def __init__(self,
                 name: str = None,
                 email: str = None,
                 imageUrl: str = None,
                 providerId: str = None,
                 accessToken: str = None,
                 refreshToken: str = None,
                 calendarSyncToken: str = None,
                 *args, **kwargs):
        self.name = name
        self.email = email
        self.imageUrl = imageUrl
        self.providerId = providerId
        self.accessToken = accessToken
        self.refreshToken = refreshToken
        self.calendarSyncToken = calendarSyncToken

    def update_token(self, token):
        self.accessToken = token.get("access_token")
        self.refreshToken = token.get("refresh_token")
        self._user.accounts[self._type] = self.json()

    def get_calendar_service(self):
        raise NotImplementedError("This is an abstract method. It must be implemented.")

    def fetch_calendar_events(self):
        raise NotImplementedError("This is an abstract method. It must be implemented.")

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        display_name = "Name"
        validation.check_min_length(display_name, value, 1)
        self._name = value

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

    @property
    def calendarSyncToken(self):
        return self._calendar_sync_token

    @calendarSyncToken.setter
    def calendarSyncToken(self, value):
        self._calendar_sync_token = value

    # Enums

    # <editor-fold desc="Account Type Enum">
    class Type(Enum):
        GOOGLE = 'google'
        MICROSOFT = 'microsoft'
    # </editor-fold>


class Google(Account):
    _token_uri = 'https://accounts.google.com/o/oauth2/token'
    _scopes = ["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile",
               'https://www.googleapis.com/auth/calendar']
    _client_id = app.config.get('GOOGLE_CLIENT_ID')
    _client_secret = app.config.get('GOOGLE_CLIENT_SECRET')

    _calendar_service = None

    def __init__(self, *args, **kwargs):
        self._type = self.Type.GOOGLE.value.lower()
        super().__init__(*args, **kwargs)

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

    def get_calendar_service(self):
        if not self._calendar_service:
            creds = self.get_credentials()
            self._calendar_service = build('calendar', 'v3', credentials=creds)
        return self._calendar_service

    def fetch_calendar_events(self):
        service = self.get_calendar_service()
        sync_token = self.calendarSyncToken
        now = datetime.utcnow().isoformat() + 'Z' if not sync_token else None
        events = []
        page_token = None
        while True:
            params = {"calendarId": "primary", "pageToken": page_token,
                      "syncToken": sync_token, "timeMin": now}
            request = service.events().list(**params)
            try:
                result = request.execute()
            except GoogleHttpError:
                return  # TODO: Handle Sync Token Invalidation: e.resp.status == 410
            page_token = result.get('nextPageToken')
            events += result.get('items')
            if not page_token:
                sync_token = result.get('nextSyncToken')
                break
        self.calendarSyncToken = sync_token
        self._user.accounts[self._type] = self.json()
        self._user.save()
        return events


class Microsoft(Account):
    _token_uri = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
    _scopes = ["Calendars.ReadWrite", "User.Read.All", "openid", "email", "offline_access"]
    _client_id = app.config.get('MICROSOFT_CLIENT_ID')
    _client_secret = app.config.get('MICROSOFT_CLIENT_SECRET')

    _calendar_service = None

    def __init__(self, *args, **kwargs):
        self._type = self.Type.MICROSOFT.value.lower()
        super().__init__(*args, **kwargs)

    def get_calendar_service(self):
        if not self._calendar_service:
            creds = {
                "access_token": self.accessToken,
                "refresh_token": self.refreshToken,
                "token_type": "Bearer"
            }
            extra = {"client_id": self._client_id, "client_secret": self._client_secret}
            self._calendar_service = self.OAuthSession(self._client_id, token=creds,
                                                       auto_refresh_kwargs=extra,
                                                       auto_refresh_url=self._token_uri,
                                                       token_updater=self.update_token)
        return self._calendar_service

    def fetch_calendar_events(self):
        service = self.get_calendar_service()
        graph_url = 'https://graph.microsoft.com/v1.0'
        sync_token = self.calendarSyncToken
        now = datetime.utcnow().isoformat() + 'Z' if not sync_token else None
        end = self.CALENDAR_MAX_END if not sync_token else None
        events = []
        page_token = None
        while True:
            params = {"StartDateTime": now, "EndDateTime": end,
                      "$deltatoken": sync_token, "$skiptoken": page_token}
            headers = {"Prefer": "odata.maxpagesize=20"}
            result = service.get(f"{graph_url}/me/calendarView/delta",
                                 params=params, headers=headers)
            try:
                result.raise_for_status()
            except requests.exceptions.HTTPError:
                logger.debug(f"Http Error - {result.json()}")
                return  # TODO: Handle Sync Token Invalidation: e.resp.status == 410
            result = result.json()
            events += result.get('value')
            next_link = result.get('@odata.nextLink')
            if not next_link:
                delta_link = result.get('@odata.deltaLink')
                sync_token = parse.parse_qs(parse.urlparse(delta_link).query).get('$deltatoken')[0]
                break
            page_token = parse.parse_qs(parse.urlparse(next_link).query).get('$skiptoken')[0]
            sync_token = None
        self.calendarSyncToken = sync_token
        self._user.accounts[self._type] = self.json()
        self._user.save()
        return events

    def fetch_event_attachments(self, event_id):
        service = self.get_calendar_service()
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
