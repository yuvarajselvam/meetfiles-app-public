import pytz
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
from app.extensions import login_manager
from app.models.base import Entity, EntityBase

logger = logging.getLogger(__name__)

CALENDAR_MAX_END = "2050-12-31 23:59:59.999Z"


class User(Entity):
    _collection = 'users'
    _resource_prefix = 'USR'
    _required_fields = ["primaryAccount", "accounts"]
    _meetspaces = _accounts = _primary_account = _timezone = _datetime_format = None

    def get_primary_account(self):
        account = None
        if self._primary_account == self.Account.Type.GOOGLE:
            account = self.Google(self.accounts['google'])
        elif self._primary_account == self.Account.Type.MICROSOFT:
            account = self.Microsoft(self.accounts['microsoft'])
        if account:
            account._user = self
        return account

    def get_primary_email(self):
        account = self.get_primary_account()
        return account.email if account else None

    def add_account(self, account, account_type, save=True):
        account_type = self.Account.Type(account_type.lower())
        self._accounts = dict() if not self._accounts else self._accounts
        if account_type == self.Account.Type.GOOGLE:
            self.accounts['google'] = self.Google(account).json()
        elif account_type == self.Account.Type.MICROSOFT:
            self.accounts['microsoft'] = self.Microsoft(account).json()
        if save:
            self.save()

    def add_meetspace(self, meetspace, role, save=True):
        if isinstance(role, str):
            role = self.Role(role.lower())
        if not isinstance(role, self.Role):
            raise ValueError(f"Role field should be of type `User.Role` or `str`, {type(role)} given.")
        self.meetspaces = dict() if not self._meetspaces else self._meetspaces
        self.meetspaces[meetspace] = role.value
        if save:
            self.save()

    # Properties

    @property
    def primaryAccount(self):
        return self._primary_account.value if self._primary_account else None

    @primaryAccount.setter
    def primaryAccount(self, value):
        self._primary_account = self.Account.Type(value.lower())

    @property
    def accounts(self):
        return self._accounts

    @accounts.setter
    def accounts(self, value):
        display_name = "Accounts"
        validation.check_instance_type(display_name, value, dict)
        self._accounts = value

    @property
    def meetspaces(self):
        return self._meetspaces

    @meetspaces.setter
    def meetspaces(self, value):
        self._meetspaces = value

    @property
    def timezone(self):
        return self._timezone

    @timezone.setter
    def timezone(self, value):
        pytz.timezone(value)  # For validating timezone value
        self._timezone = value

    @property
    def datetimeFormat(self):
        return self._datetime_format

    @datetimeFormat.setter
    def datetimeFormat(self, value):
        self._datetime_format = value

    # Enums

    # <editor-fold desc="User Role Enum">
    class Role(Enum):
        OWNER = 'owner'
        ADMIN = 'admin'

    # </editor-fold>

    # Nested classes

    class Account(EntityBase):
        _required_fields = ["email", "name"]

        _type = ''
        _user = None
        _name = _email = _image_url = _provider_id = \
            _access_token = _refresh_token = _calendar_sync_token = None

        def update_token(self, token):
            self.accessToken = token.get("access_token")
            self.refreshToken = token.get("refresh_token")
            self._user.accounts[self._type] = self.json()

        @property
        def name(self):
            return self._name

        @name.setter
        def name(self, value):
            display_name = "Name"
            validation.check_instance_type(display_name, value, str)
            validation.check_min_length(display_name, value, 1)
            self._name = value

        @property
        def email(self):
            return self._email

        @email.setter
        def email(self, value):
            display_name = "Email"
            validation.check_instance_type(display_name, value, str)
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
            Google = self

            class Credentials(GoogleCredentials):
                def refresh(self, request):
                    super().refresh(request)
                    token = {"access_token": self.token, "refresh_token": self._refresh_token}
                    Google.update_token(token)

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

        def fetch_google_calendar_events(self):
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
                                                           auto_refresh_url=self._token_uri)
            return self._calendar_service

        def fetch_outlook_calendar_events(self):
            service = self.get_calendar_service()
            graph_url = 'https://graph.microsoft.com/v1.0'
            sync_token = self.calendarSyncToken
            now = datetime.utcnow().isoformat() + 'Z' if not sync_token else None
            end = CALENDAR_MAX_END if not sync_token else None
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
                self.token = token

            def request(self, method, url, data=None, headers=None, **kwargs):
                result = super().request(method, url, data=None, headers=None, **kwargs)
                error = result.json().get('error')
                if isinstance(error, dict) and (error.get('code') == "InvalidAuthenticationToken"):
                    self.refresh_token(self.auto_refresh_url)
                    result = super().request(method, url, data=None, headers=None, **kwargs)
                return result

    # Flask login - Properties

    _is_authenticated = False
    _is_active = True
    _is_anonymous = False

    def authenticate(self):
        self._is_authenticated = True

    def is_authenticated(self):
        return self._is_authenticated

    def is_active(self):
        return self._is_active

    def is_anonymous(self):
        return self._is_anonymous

    def get_id(self):
        return self.id


# Flask login - User loader

@login_manager.user_loader
def load_user(user_id):
    return User.find_one({"id": user_id})
