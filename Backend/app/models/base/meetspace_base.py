from app.utils import validation
from app.models.base.entity import Entity


class MeetspaceBase(Entity):
    _collection = 'meetspaces'
    _resource_prefix = 'MSP'
    _required_fields = ["name", "owners", "meetspace"]

    def __init__(self,
                 name: str = None,
                 owners: list = None,
                 imageUrl: str = None,
                 meetsections: list = None,
                 createdBy: str = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.owners = owners or []
        self.imageUrl = imageUrl
        self.meetsections = meetsections or []
        self.createdBy = createdBy

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
