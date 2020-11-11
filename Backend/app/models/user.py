from app.extensions import login_manager
from app.models.base.user_base import UserBase
from app.models.base.account import Account, Google, Microsoft


class User(UserBase):
    def get_primary_account(self):
        account = None
        if self.primaryAccount == Account.Type.GOOGLE.value:
            account = Google(**self.accounts['google'])
        elif self.primaryAccount == Account.Type.MICROSOFT.value:
            account = Microsoft(**self.accounts['microsoft'])
        if account:
            account._user = self
        return account

    def get_primary_email(self):
        account = self.get_primary_account()
        return account.email if account else None

    def add_account(self, account, account_type, save=True):
        account_type = Account.Type(account_type.lower())
        if account_type == Account.Type.GOOGLE:
            self.accounts['google'] = Google(account).json()
        elif account_type == Account.Type.MICROSOFT:
            self.accounts['microsoft'] = Microsoft(account).json()
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
