import uuid
import inspect
from datetime import datetime

from app.extensions import db
from app.utils import validation


class EntityBase:
    _collection = None
    _required_fields = []

    def __init__(self, *args, **kwargs):
        [setattr(self, k, v) for arg in args for k, v in arg.items() if hasattr(self, k)]
        [setattr(self, k, v) for k, v in kwargs.items() if hasattr(self, k)]

    def validate(self):
        for field in self._required_fields:
            if not getattr(self, field):
                formatted_field_name = ''.join(map(lambda x: x if x.islower() else " " + x, field)).title()
                raise KeyError(f"{formatted_field_name} is mandatory.")

    def json(self):
        attributes = inspect.getmembers(self, lambda a: not (inspect.isroutine(a)))
        return dict([(a, v) for a, v in attributes if (not a.startswith('_')) and a[0].islower() and v])


class Entity(EntityBase):
    _resource_prefix = ''

    _id = \
        _updated_at = \
        _created_at = None

    def generate_id(self):
        return self._resource_prefix + uuid.uuid4().hex

    def save(self, validate=True, session=None):
        if validate:
            self.validate()

        if not self.id:
            self.id = self.generate_id()

        if not self._created_at:
            self._created_at = datetime.utcnow()

        self._updated_at = datetime.utcnow()
        collection = db.get_conn()[self._collection]
        collection.update_one({"id": self.id}, {"$set": self.json()},
                              upsert=True, session=session)

    @classmethod
    def bulk_write(cls, operations):
        collection = db.get_conn()[cls._collection]
        with db.get_session() as session:
            with session.start_transaction():
                result = collection.bulk_write(operations, ordered=False, session=session)
        print("Success:", result.bulk_api_result)
        return result

    @classmethod
    def find_one(cls, query=None, session=None):
        document = db.get_conn()[cls._collection].find_one(query, session=session)
        if not document:
            return
        return cls(document)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        validation.check_instance_type("id", value, str)
        self._id = value

    @property
    def createdAt(self):
        return self._created_at

    @createdAt.setter
    def createdAt(self, value):
        self._created_at = value

    @property
    def updatedAt(self):
        return self._updated_at

    @updatedAt.setter
    def updatedAt(self, value):
        self._updated_at = value
