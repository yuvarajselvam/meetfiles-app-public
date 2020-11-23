from flask_login import current_user

from app.models.event import Event
from app.models.base.meetsection_base import MeetsectionBase


class Meetsection(MeetsectionBase):

    _PERSONAL_DESC = "This is your personal meetsection."

    def json(self, deep=False):
        result = super().json()
        current_user_email = current_user.get_primary_email()
        if result["createdBy"] == current_user_email:
            result["type"] = "self"
        elif result["createdBy"] == "system":
            result["type"] = "default"
        else:
            result["type"] = "shared"
        if deep:
            result["events"] = []
            events = self.fetch_events()
            for event in events:
                result["events"].append(Event(**event).to_api_object())
        return result

    def add_user(self, user_email, owner=False):
        role = self.Role.USER.value if not owner else self.Role.OWNER.value
        self.members.append({"email": user_email, "role": role})

    def remove_user(self, user_email):
        self.members = [member for member in self.members if not member["email"] == user_email]

    @classmethod
    def get_default_name(cls, user_name):
        return user_name + "'s Meetsection" if user_name else "Default Meetsection"

    @classmethod
    def get_personal_desc(cls):
        return cls._PERSONAL_DESC

    @classmethod
    def get_default(cls, email):
        return cls.find_one({"members.email": email, "createdBy": "system"})

    @classmethod
    def fetch_for_user(cls, user_email):
        return cls.find({"members.email": user_email})

    def fetch_events(self):
        from app.models.event import Event
        self.members = self.members
        return Event.find({"status": {"$ne": "cancelled"}, "meetsection": self.id})
