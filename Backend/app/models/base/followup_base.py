from app.models.base.entity import Entity


class FollowUpBase(Entity):
    _collection = 'follow_ups'
    _resource_prefix = 'FWP'
    _required_fields = []

    def __init__(self,
                 events: list = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events = events or list()

    @property
    def events(self):
        return self._events

    @events.setter
    def events(self, value):
        self._events = value
