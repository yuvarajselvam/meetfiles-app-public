from app.models.base.followup_base import FollowUpBase


class FollowUp(FollowUpBase):
    def add_event(self, event):
        if not isinstance(event, str):
            event = event.id
        self.events.append(event)
