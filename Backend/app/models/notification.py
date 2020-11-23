from app.models.base.notification_base import NotificationBase


class Notification(NotificationBase):
    def send(self):
        self.save()

