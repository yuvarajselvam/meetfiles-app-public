from flask_pymongo import PyMongo


class MongoDB:
    mongo = None
    uri = None
    database = None

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.uri = app.config['MONGODB_URI']
        self.database = app.config['MONGODB_DB']
        self.mongo = PyMongo(app, self.uri, connect=True)

    def get_conn(self):
        try:
            return self.mongo.cx[self.database]
        except Exception as e:
            raise ConnectionError

    def get_session(self):
        try:
            return self.mongo.cx.start_session()
        except Exception as e:
            raise ConnectionError
