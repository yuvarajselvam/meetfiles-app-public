import pytz

from enum import Enum
from typing import Union

from app.models.base.entity import Entity
from app.models.base.account import Account


class UserBase(Entity):
    _collection = 'users'
    _resource_prefix = 'USR'
    _required_fields = ["primaryAccount"]

    def __init__(self,
                 primaryAccount: Union[Account.Type, str] = None,
                 accounts: list = None,
                 meetspaces: dict = None,
                 timeZone: str = None,
                 dateFormat: str = "DD-MM-YYYY",
                 timeFormat: str = "HH:mm",
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.primaryAccount = primaryAccount
        self.accounts = accounts or []
        self.meetspaces = meetspaces or dict()
        self.timeZone = timeZone
        self.dateFormat = dateFormat
        self.timeFormat = timeFormat

    # Properties

    @property
    def primaryAccount(self):
        return self._primary_account.value

    @primaryAccount.setter
    def primaryAccount(self, value):
        if not value:
            return
        if isinstance(value, str):
            self._primary_account = Account.Type(value.lower())
        elif isinstance(value, Account.Type):
            self._primary_account = value
        else:
            raise ValueError(f'Primary Account should be of type '
                             f'`str` or `Account.Type` not {type(value)}')

    @property
    def accounts(self):
        return self._accounts

    @accounts.setter
    def accounts(self, value):
        self._accounts = value

    @property
    def meetspaces(self):
        return self._meetspaces

    @meetspaces.setter
    def meetspaces(self, value):
        self._meetspaces = value

    @property
    def timeZone(self):
        return self._time_zone

    @timeZone.setter
    def timeZone(self, value):
        if not value:
            return
        pytz.timezone(value)  # For validating timezone value
        self._time_zone = value

    @property
    def dateFormat(self):
        return self._date_format

    @dateFormat.setter
    def dateFormat(self, value):
        self._date_format = value

    @property
    def timeFormat(self):
        return self._time_format

    @timeFormat.setter
    def timeFormat(self, value):
        self._time_format = value

    # Enums

    # <editor-fold desc="User Role Enum">
    class Role(Enum):
        OWNER = 'owner'
        ADMIN = 'admin'
    # </editor-fold>
