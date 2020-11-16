from app.extensions import login_manager
from app.models.base.user_base import UserBase
from app.models.base.account import Account, Google, Microsoft


class User(UserBase):
    def get_account(self, account_type):
        acc = next(filter(lambda a: a["type"] == account_type, self.accounts), None)
        if account_type == Account.Type.GOOGLE.value:
            account = Google(**acc)
        elif account_type == Account.Type.MICROSOFT.value:
            account = Microsoft(**acc)
        else:
            raise ValueError('Invalid account type')
        account._user = self
        return account

    def get_account_by_email(self, email):
        acc = next(filter(lambda a: a["email"] == email, self.accounts), None)
        if not acc:
            return
        return self.get_account(acc["type"])

    def get_primary_account(self):
        return self.get_account(self.primaryAccount)

    def get_primary_email(self):
        account = self.get_primary_account()
        return account.email if account else None

    def add_account(self, account, account_type, save=True):
        account_type = Account.Type(account_type.lower())
        if account_type == Account.Type.GOOGLE:
            self.accounts.append(Google(**account).json())
        elif account_type == Account.Type.MICROSOFT:
            self.accounts.append(Microsoft(**account).json())
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

    def sync_calendars(self):
        print(self.accounts)
        for acc in self.accounts:
            account = self.get_account(acc["type"])
            print(account.json())
            calendar = account.get_calendar()
            print(calendar.json())
            calendar.sync_events()

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
