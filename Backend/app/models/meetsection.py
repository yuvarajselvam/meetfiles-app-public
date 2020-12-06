from datetime import datetime
from flask_login import current_user

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
        current_user_email = current_user.get_primary_email()
        if result["createdBy"] == current_user_email:
            result["type"] = "self"
        elif result["createdBy"] == "system":
            result["type"] = "default"
        else:
            result["type"] = "shared"
        return result

    def to_full_object(self):
        result = self.to_simple_object()
        result["events"] = {"recurring": [],
                            "nonRecurring": []}
        events = self.fetch_events()
        for event in events:
            e = Event(**event)
            category = "recurring" if e.isRecurring else "nonRecurring"
            result["events"][category].append(e.to_simple_object())
        return result

    def add_user(self, user_email, owner=False):
        role = self.Role.USER.value if not owner else self.Role.OWNER.value
        self.members.append({"email": user_email, "role": role})

    def remove_user(self, user_email):
        self.members = [member for member in self.members if not member["email"] == user_email]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_firebase()

    def update_firebase(self):
        path = f"meetsections/{self.id}"
        firebase_service.db_insert(path, self.to_full_object())

    @classmethod
    def bulk_update_firebase(cls, meetsection_ids):
        insert_obj = dict()
        meetsections = Meetsection.find({"id": {"$in": meetsection_ids}})
        for m in meetsections:
            insert_obj[f"meetsections/{m['id']}"] = Meetsection(**m).to_full_object()
        firebase_service.db_insert(insert_obj)

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
        return Event.find({"status": {"$ne": "cancelled"}, "meetsections.id": self.id})
