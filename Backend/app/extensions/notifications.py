from firebase_admin import initialize_app, credentials as cred, messaging


class NotificationService:
    service = None

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        path = app.config.get('FIREBASE_CREDS_PATH')
        self.service = initialize_app(credential=cred.Certificate(path))

    @staticmethod
    def send(token, data, title, body):
        notification_obj = messaging.Notification(title=title, body=body)
        message = messaging.Message(data=data, notification=notification_obj, token=token)
        messaging.send(message)
