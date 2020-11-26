from datetime import datetime

from pymongo.operations import InsertOne

from app.extensions import firebase_service
from app.models.base.notification_base import NotificationBase


class Notification(NotificationBase):
    def set_user(self, user):
        self.user = user.id
        self._user_obj = user

    def push(self, save=True):
        if not self.user:
            raise ValueError("User not set")
        if save:
            self.save()
        tokens = self._user_obj.notifTokens
        firebase_service.notify_all(tokens, {}, self.title, self.body)

    @classmethod
    def push_all(cls, title, body, users):
        utc_now = datetime.utcnow()
        operations = []
        tokens = []
        for user in users:
            notif = cls(title, body, False)
            tokens += user.notifTokens
            notif.id = notif.generate_id()
            notif.createdAt = utc_now
            notif.updatedAt = utc_now
            operations.append(InsertOne(notif.json()))
        cls.bulk_write(operations)
        firebase_service.notify_all(tokens, {}, title, body)

