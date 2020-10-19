from enum import Enum

from app.utils import validation
from app.extensions import login_manager
from app.models.base import Entity, EntityBase


class User(Entity):
    _collection = 'users'
    _resource_prefix = 'USR'
    _required_fields = ["primaryAccount", "accounts"]
    _meetspaces = \
        _accounts = \
        _primary_account = None

    def get_primary_account_json(self):
        return self.accounts[self.primaryAccount]

    def get_primary_email(self):
        return self.get_primary_account_json()['email']

    def add_account(self, account, account_type, save=True):
        self.Account.Type(account_type.lower())  # For validating account type
        self._accounts = dict() if not self._accounts else self._accounts
        self.accounts[account_type.lower()] = self.Google(account).json()
        if save:
            self.save()

    def add_meetspace(self, meetspace, role, save=True):
        if isinstance(role, str):
            role = self.Role(role.lower())
        if not isinstance(role, self.Role):
            raise ValueError(f"Role field should be of type User.Role or str, {type(role)} given.")
        self.meetspaces = dict() if not self._meetspaces else self._meetspaces
        self.meetspaces[meetspace] = role
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
        _name = \
            _email = \
            _image_url = None

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
        _refresh_token = None

        def __init__(self, *args, **kwargs):
            self._type = self.Type.GOOGLE.value.lower()
            super().__init__(*args, **kwargs)

        # Properties

        @property
        def refreshToken(self):
            return self._refresh_token

        @refreshToken.setter
        def refreshToken(self, value):
            self._refresh_token = value

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
