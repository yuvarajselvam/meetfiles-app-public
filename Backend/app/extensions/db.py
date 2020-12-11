from flask_pymongo import PyMongo
from pymongo import TEXT
from pymongo.errors import CollectionInvalid, OperationFailure


class MongoDB:
    mongo = None
    uri = None
    database = None
    COLLECTIONS = ['users', 'events', 'recurring_exception_events', 'calendars', 'meetsections']

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.uri = app.config['MONGODB_URI']
        self.database = app.config['MONGODB_DB']
        self.mongo = PyMongo(app, self.uri, connect=True)

        # Create Collections
        for collection in self.COLLECTIONS:
            try:
                self.mongo.cx[self.database].create_collection(collection)
            except CollectionInvalid:
                pass

        # Create Index
        ev_index_weights = {'title': 2, 'description': 1}
        ev_index_keys = [('title', TEXT), ('description', TEXT)]
        try:
            events = self.mongo.cx[self.database]["events"]
            events.create_index(ev_index_keys, weights=ev_index_weights,
                                default_language="english")
        except OperationFailure:
            pass

        try:
            exceptions = self.mongo.cx[self.database]["recurring_exception_events"]
            exceptions.create_index(ev_index_keys, weights=ev_index_weights,
                                    default_language="english")
        except OperationFailure:
            pass

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
