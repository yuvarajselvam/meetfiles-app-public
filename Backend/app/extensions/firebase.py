import json
from firebase_admin import initialize_app, credentials as cred, db


class FirebaseService:
    service = None

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        creds = cred.Certificate(app.config.get('FIREBASE_CREDS_PATH'))
        with open(app.config.get('FIREBASE_OPTS_PATH')) as f:
            options = json.load(f)
        self.service = initialize_app(credential=creds, options=options)

    @staticmethod
    def db_insert(path, value):
        db.reference(path).set(value)

    @staticmethod
    def db_update(value):
        db.reference().update(value)

    @staticmethod
    def notify(user_id, title, body):
        notif_ref = db.reference(f'users/{user_id}/notifications')
        notif_ref.push({"title": title, "body": body})

    @staticmethod
    def notify_all(user_ids, title, body):
        users_ref = db.reference('users')
        key = None
        update_obj = dict()
        for u_id in user_ids:
            if key is None:
                notif_ref = users_ref.child(f'{u_id}/notifications')
                key = notif_ref.push({"title": title, "body": body}).key
            else:
                update_obj[f'{u_id}/notifications/{key}'] = {"title": title, "body": body}
        if update_obj:
            users_ref.update(update_obj)
