import uuid
import inspect
from datetime import datetime

from app.extensions import db


class EntityBase:
    _collection = None
    _required_fields = []

    def validate(self):
        for f in self._required_fields:
            if not getattr(self, f):
                formatted_field_name = ''.join(map(lambda x: x if x.islower() else " " + x, f)).title()
                raise KeyError(f"{formatted_field_name} is mandatory.")

    def json(self):
        attributes = inspect.getmembers(self, lambda a: not (inspect.isroutine(a)))
        return dict([(a, v) for a, v in attributes if (not a.startswith('_')) and a[0].islower() and v])


class Entity(EntityBase):
    _resource_prefix = ''

    def __init__(self,
                 id: str = None,
                 createdAt: datetime = None,
                 updatedAt: datetime = None,
                 *args, **kwargs):
        self.id = id
        self.createdAt = createdAt
        self.updatedAt = updatedAt

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
        result = None
        if operations:
            collection = db.get_conn()[cls._collection]
            with db.get_session() as session:
                with session.start_transaction():
                    result = collection.bulk_write(operations, ordered=False, session=session)
        return result

    @classmethod
    def find_one(cls, query=None, session=None, deleted=False):
        if not deleted:
            query["deletedAt"] = {"$exists": False}
        document = db.get_conn()[cls._collection].find_one(query, session=session)
        if not document:
            return
        return cls(**document)

    @classmethod
    def find(cls, query=None, session=None):
        documents = db.get_conn()[cls._collection].find(query, session=session)
        if not documents:
            return []
        return list(documents)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
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
