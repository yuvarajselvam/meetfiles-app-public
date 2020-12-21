from datetime import datetime

from app.models.event import Event
from app.extensions import firebase_service
from app.models.base.meetsection_base import MeetsectionBase


class Meetsection(MeetsectionBase):

    _PERSONAL_DESC = "This is your personal meetsection."

    def to_simple_object(self):
        result = super().json()
        for k, v in result.items():
            if isinstance(v, datetime):
                result[k] = v.isoformat()
        return result

    def to_full_object(self, user_id, timezone=None):
        result = self.to_simple_object()
        result["events"] = []
        events = self.fetch_events(user_id)
        for event in events:
            e = Event(**event)
            if e.isRecurring:
                result["events"].append(e.expand_for_firebase(timezone=timezone))
            else:
                result["events"].append(e.to_simple_object(timezone=timezone))
        return result

    def add_user(self, user_email, owner=False):
        role = self.Role.USER.value if not owner else self.Role.OWNER.value
        self.remove_user(user_email)
        self.members.append({"email": user_email, "role": role})

    def remove_user(self, user_email):
        self.members = [member for member in self.members if not member["email"] == user_email]

    def get_users(self):
        query = {"accounts.email": {"$in": [member["email"] for member in self.members]}}
        from app.models.user import User
        return User.find(query)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_firebase(self.get_users())

    def update_firebase(self, users):
        update_obj = dict()
        for u in users:
            path = f"users/{u['id']}/meetsections/{self.id}"
            update_obj[path] = self.to_full_object(u['id'], timezone=u['timeZone'])
        firebase_service.db_update(update_obj)

    @classmethod
    def bulk_update_firebase(cls, meetsection_ids, user):
        insert_obj = dict()
        meetsections = Meetsection.find({"id": {"$in": meetsection_ids}})
        for m in meetsections:
            path = f"users/{user.id}/meetsections/{m['id']}"
            insert_obj[path] = Meetsection(**m).to_full_object(user.id, timezone=user.timeZone)
        firebase_service.db_update(insert_obj)

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

    def fetch_events(self, user_id):
        from app.models.event import Event
        return Event.find({"status": {"$ne": "cancelled"},
                           "meetsections": self.id,
                           "user": user_id,
                           "$or": [{"isDeleted": {"$exists": False}},
                                   {"isDeleted": False}]})
