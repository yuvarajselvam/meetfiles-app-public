from app.utils import validation
from app.models.base import Entity


class Meetspace(Entity):
    _collection = 'meetspaces'
    _resource_prefix = 'MSP'
    _required_fields = ["name", "owners", "meetspace"]

    _name = \
        _owners = \
        _image_url = \
        _meetsections = \
        _created_by = None

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
    def imageUrl(self):
        return self._image_url

    @imageUrl.setter
    def imageUrl(self, value):
        validation.check_regex_match("Image URL", value, validation.URL_REGEX)
        self._image_url = value

    @property
    def owners(self):
        return self._owners

    @owners.setter
    def owners(self, value):
        self._owners = value

    @property
    def createdBy(self):
        return self._created_by

    @createdBy.setter
    def createdBy(self, value):
        self._created_by = value
