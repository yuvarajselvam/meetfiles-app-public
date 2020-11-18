from app.utils import validation
from app.models.base.entity import Entity


class MeetsectionBase(Entity):
    _collection = 'meetsections'
    _resource_prefix = 'SEC'
    _required_fields = ["name"]

    def __init__(self,
                 name: str = None,
                 members: list = None,
                 meetspace: str = None,
                 createdBy: str = None,
                 description: str = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.members = members or []
        self.meetspace = meetspace
        self.createdBy = createdBy
        self.description = description

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
