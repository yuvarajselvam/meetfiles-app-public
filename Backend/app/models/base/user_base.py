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
                 accounts: dict = None,
                 meetspaces: dict = None,
                 timezone: str = None,
                 datetimeFormat: str = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.primaryAccount = primaryAccount
        self.accounts = accounts or dict()
        self.meetspaces = meetspaces or dict()
        self.timezone = timezone
        self.datetimeFormat = datetimeFormat

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
            pass
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
    def timezone(self):
        return self._timezone

    @timezone.setter
    def timezone(self, value):
        if not value:
            return
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
