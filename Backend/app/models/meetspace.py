from app.utils import validation
from app.models.base import Entity


class Meetspace(Entity):
    _collection = 'meetspaces'
    _resource_prefix = 'MSP'
    _required_fields = ["name", "owners"]

    _name = \
        _owners = \
        _created_by = None

    # Properties

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def owners(self):
        return self._owners

    @owners.setter
    def owners(self, value):
        display_name = "Owners"
        validation.check_instance_type(display_name, value, list)
        self._owners = value

    @property
    def createdBy(self):
        return self._created_by

    @createdBy.setter
    def createdBy(self, value):
        self._created_by = value
