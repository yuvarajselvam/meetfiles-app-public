import datetime

from enum import Enum

from app.utils import datetime as dt_util
from app.models.base.entity import Entity


class EventBase(Entity):
    _collection = 'events'
    _resource_prefix = 'EVT'
    _required_fields = []

    def __init__(self,
                 meetspace: str = None,
                 meetsection: str = None,
                 user: str = None,
                 title: str = None,
                 start: datetime.datetime = None,
                 end: datetime.datetime = None,
                 originalStart: datetime.datetime = None,
                 organizer: str = None,
                 attendees: dict = None,
                 isAllDay: bool = None,
                 location: str = None,
                 description: str = None,
                 conferenceData: dict = None,
                 attachments: dict = None,
                 status: str = None,
                 isRecurring: bool = None,
                 recurrence: str = None,
                 transparency: str = None,
                 webLink: str = None,
                 provider: str = None,
                 providerId: str = None,
                 created: datetime.datetime = None,
                 updated: datetime.datetime = None,
                 isDeleted: bool = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.meetspace = meetspace
        self.meetsection = meetsection
        self.user = user
        self.title = title
        self.start = start
        self.end = end
        self.originalStart = originalStart
        self.organizer = organizer
        self.attendees = attendees or dict()
        self.isAllDay = isAllDay
        self.location = location
        self.description = description
        self.conferenceData = conferenceData or dict()
        self.attachments = attachments or dict()
        self.status = status
        self.isRecurring = isRecurring
        self.recurrence = recurrence
        self.transparency = transparency
        self.webLink = webLink
        self.provider = provider
        self.providerId = providerId
        self.created = created
        self.updated = updated
        self.isDeleted = isDeleted

    # Properties

    @property
    def meetspace(self):
        return self._meetspace

    @meetspace.setter
    def meetspace(self, value):
        self._meetspace = value

    @property
    def meetsection(self):
        return self._meetsection

    @meetsection.setter
    def meetsection(self, value):
        self._meetsection = value

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, value):
        self._user = value

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value

    @property
    def originalStart(self):
        return self._original_start

    @originalStart.setter
    def originalStart(self, value):
        self._original_start = dt_util.get_datetime(value)

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, value):
        self._start = dt_util.get_datetime(value)

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, value):
        self._end = dt_util.get_datetime(value)

    @property
    def organizer(self):
        return self._organizer

    @organizer.setter
    def organizer(self, value):
        self._organizer = value

    @property
    def attendees(self):
        return self._attendees

    @attendees.setter
    def attendees(self, value):
        self._attendees = value

    @property
    def isAllDay(self):
        return self._is_all_day

    @isAllDay.setter
    def isAllDay(self, value):
        self._is_all_day = value

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value):
        self._location = value

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value

    @property
    def attachments(self):
        return self._attachments

    @attachments.setter
    def attachments(self, value):
        self._attachments = value

    @property
    def status(self):
        return self._status.value if self._status else None

    @status.setter
    def status(self, value):
        if not value:
            return
        self._status = self.Status(value.lower())

    @property
    def recurrence(self):
        return self._recurrence

    @recurrence.setter
    def recurrence(self, value):
        self._recurrence = value

    @property
    def isRecurring(self):
        return self._is_recurring

    @isRecurring.setter
    def isRecurring(self, value):
        self._is_recurring = value

    @property
    def transparency(self):
        return self._transparency.value if self._transparency else None

    @transparency.setter
    def transparency(self, value):
        if not value:
            return
        self._transparency = self.Transparency(value.lower())

    @property
    def webLink(self):
        return self._web_link

    @webLink.setter
    def webLink(self, value):
        self._web_link = value

    @property
    def provider(self):
        return self._provider

    @provider.setter
    def provider(self, value):
        self._provider = value

    @property
    def providerId(self):
        return self._provider_id

    @providerId.setter
    def providerId(self, value):
        self._provider_id = value

    @property
    def created(self):
        return self._created

    @created.setter
    def created(self, value):
        self._created = dt_util.get_datetime(value)

    @property
    def updated(self):
        return self._updated

    @updated.setter
    def updated(self, value):
        self._updated = dt_util.get_datetime(value)

    @property
    def isDeleted(self):
        return self._is_deleted

    @isDeleted.setter
    def isDeleted(self, value):
        self._is_deleted = value

    # Enums

    # <editor-fold desc="Event Status Enum">
    class Status(Enum):
        CONFIRMED = "confirmed"
        TENTATIVE = "tentative"
        CANCELLED = "cancelled"

    # </editor-fold>

    # <editor-fold desc="Event Transparency Enum">
    class Transparency(Enum):
        OPAQUE = "opaque"
        TRANSPARENT = "transparent"
    # </editor-fold>


# <editor-fold desc="Event Status Enum" default="collapsed">
class VideoConferenceType(Enum):
    ZOOM = "zoom"
    GOOGLE_MEET = "google_meet"
# </editor-fold>
