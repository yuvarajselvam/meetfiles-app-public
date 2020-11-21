from app.models.event import Event
from app.models.base.followup_base import FollowUpBase


class FollowUp(FollowUpBase):
    def add_event(self, event):
        if isinstance(event, Event):
            event = event.id
        self.events.append(event)
