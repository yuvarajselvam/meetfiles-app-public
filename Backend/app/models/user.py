import pytz

from enum import Enum
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

from app import app
from app.utils import validation
from app.extensions import login_manager
from app.models.base import Entity, EntityBase


class User(Entity):
    _collection = 'users'
    _resource_prefix = 'USR'
    _required_fields = ["primaryAccount", "accounts"]
    _meetspaces = _accounts = _primary_account = _timezone = _datetime_format = None

    def get_primary_account(self):
        if self._primary_account == self.Account.Type.GOOGLE:
            return self.Google(self.accounts['google'])
        elif self._primary_account == self.Account.Type.AZURE:
            return self.Azure(self.accounts['azure'])

    def get_primary_email(self):
        return self.get_primary_account().email

    def add_account(self, account, account_type, save=True):
        account_type = self.Account.Type(account_type.lower())
        self._accounts = dict() if not self._accounts else self._accounts
        if account_type == self.Account.Type.GOOGLE:
            self.accounts['google'] = self.Google(account).json()
        elif account_type == self.Account.Type.AZURE:
            self.accounts['azure'] = self.Azure(account).json()
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
        _name = _email = _image_url = None

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

        # Enums

        # <editor-fold desc="Account Type Enum">
        class Type(Enum):
            GOOGLE = 'google'
            AZURE = 'azure'
        # </editor-fold>

    class Google(Account):
        _refresh_token = _calendar_sync_token = None
        _token_uri = 'https://accounts.google.com/o/oauth2/token'
        _scopes = ["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile",
                   'https://www.googleapis.com/auth/calendar']
        _client_id = app.config.get('GOOGLE_CLIENT_ID')
        _client_secret = app.config.get('GOOGLE_CLIENT_SECRET')

        _calendar_service = None

        def __init__(self, *args, **kwargs):
            self._type = self.Type.GOOGLE.value.lower()
            super().__init__(*args, **kwargs)

        def get_calendar_service(self):
            if not self._calendar_service:
                auth_user_info = {
                    'token_uri': self._token_uri,
                    'client_id': self._client_id,
                    'client_secret': self._client_secret,
                    'refresh_token': self._refresh_token,
                    'scopes': self._scopes
                }
                creds = Credentials.from_authorized_user_info(auth_user_info)
                self._calendar_service = build('calendar', 'v3', credentials=creds)
            return self._calendar_service

        def fetch_google_calendar_events(self):
            service = self.get_calendar_service()
            sync_token = self.calendarSyncToken
            now = datetime.utcnow().isoformat() + 'Z' if sync_token else None
            events = []
            page_token = None
            while True:
                params = {"calendarId": "primary", "pageToken": page_token,
                          "syncToken": sync_token, "timeMin": now}
                request = service.events().list(**params)
                try:
                    result = request.execute()
                except HttpError:
                    return  # TODO: Handle Sync Token Invalidation: e.resp.status == 410
                page_token = result.get('nextPageToken')
                events += result.get('items')
                if not page_token:
                    sync_token = result.get('nextSyncToken')
                    break
            self.calendarSyncToken = sync_token
            return events

        # Properties

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

    class Azure(Account):
        def __init__(self, *args, **kwargs):
            self._type = self.Type.AZURE.value.lower()
            super().__init__(*args, **kwargs)

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
