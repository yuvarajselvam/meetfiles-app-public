from firebase_admin import initialize_app, credentials as cred, db


class FirebaseService:
    service = None

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        path = app.config.get('FIREBASE_CREDS_PATH')
        self.service = initialize_app(credential=cred.Certificate(path))

    @staticmethod
    def db_insert(path, value):
        db.reference(path).set(value)

    @staticmethod
    def notify(token, data, title, body):
        pass

    @staticmethod
    def notify_all(tokens, data, title, body):
        pass
