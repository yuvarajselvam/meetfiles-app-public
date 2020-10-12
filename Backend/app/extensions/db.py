import os
from pymongo import MongoClient
from urllib.parse import quote_plus


class MongoDB:
    def __init__(self):
        self.app = None
        self.client = None

    def init_app(self, app):
        self.app = app
        self.connect()

    def connect(self):
        user = os.getenv("MONGODB_USER")
        password = os.getenv("MONGODB_PASSWORD")
        host = os.getenv("MONGODB_HOST_URL")
        uri = "mongodb://%s:%s@%s" % (quote_plus(user), quote_plus(password), host)
        self.client = MongoClient(uri)
        return self.client

    def get_db(self):
        if not self.client:
            return self.connect()
        return self.client
