from app.utils import validation
from app.models.base import Entity


class Meetsection(Entity):
    _collection = 'meetsections'
    _resource_prefix = 'SEC'
    _required_fields = ["name", "members"]

    _DEFAULT_DESC = "This is your personal meetsection."

    _name = \
        _events = \
        _members = \
        _meetspace = \
        _created_by = \
        _description = None

    @classmethod
    def get_default_name(cls, user_name):
        return user_name + "'s Meetsection"

    @classmethod
    def get_default_desc(cls):
        return cls._DEFAULT_DESC

    # Properties

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        display_name = "Name"
        validation.check_min_length(display_name, value, 3)
        self._name = value

    @property
    def events(self):
        return self._events

    @events.setter
    def events(self, value):
        display_name = "Events"
        validation.check_instance_type(display_name, value, list)
        self._events = value

    @property
    def members(self):
        return self._members

    @members.setter
    def members(self, value):
        display_name = "Members"
        validation.check_instance_type(display_name, value, list)
        self._members = value

    @property
    def meetspace(self):
        return self._meetspace

    @meetspace.setter
    def meetspace(self, value):
        self._meetspace = value

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value

    @property
    def createdBy(self):
        return self._created_by

    @createdBy.setter
    def createdBy(self, value):
        self._created_by = value