import datetime
from enum import Enum

from pymongo.operations import UpdateOne

from app.models.base import Entity
from app.utils import datetime as dt_util


class Event(Entity):
    _collection = 'events'
    _resource_prefix = 'EVT'
    _required_fields = []

    _meetspace = \
        _meetsection = \
        _user = \
        _summary = \
        _start = \
        _end = \
        _original_start = \
        _organizer = \
        _attendees = \
        _description = \
        _attachments = \
        _status = \
        _is_recurring = \
        _recurrence = \
        _transparency = \
        _web_link = \
        _provider_id = \
        _created_by = \
        _created = \
        _updated = None

    @classmethod
    def sync_google_events(cls, events, meetspace, meetsection, user):
        if events:
            bulk_write_data = {"events": [], "recurring_exception_events": []}
            REE = RecurringExceptionEvent
            for ev in events:
                recurring_event_id = ev.get("recurringEventId")
                params = {"meetspace": meetspace, "meetsection": meetsection, "user": user}
                event = Event(params) if not recurring_event_id else REE(params)
                event.recurringEventProviderId = recurring_event_id
                event.from_google_event(ev)
                operation = UpdateOne({"providerId": event.providerId}, {"$set": event.json()}, upsert=True)
                bulk_write_data[event._collection].append(operation)
            events_result = Event.bulk_write(bulk_write_data['events'])
            ree_result = REE.bulk_write(bulk_write_data['recurring_exception_events'])
            return events_result, ree_result

    def from_google_event(self, ev):
        def _get_datetime(obj):
            if obj and "dateTime" in obj:
                return [obj["dateTime"], obj.get("timeZone")]
            elif obj and "date" in obj:
                return [obj["date"], obj.get("timeZone")]

        utc_now = datetime.datetime.utcnow()
        attendees = ev.get("attendees", [])
        self.attendees = []
        for attendee in attendees:
            response = attendee.get("responseStatus")
            response = "notResponded" if response == "needsAction" else response
            self.attendees.append({
                "email": attendee.get("email"),
                "responseStatus": response
            })

        attachments = ev.get("attachments")
        if attachments:
            for attachment in attachments:
                self.attachments.append({
                    "id": attachment.get("id"),
                    "url": attachment.get("fileUrl"),
                    "type": attachment.get("mimeType"),
                    "external": True
                })

        self.start = _get_datetime(ev.get("start"))
        self.originalStart = _get_datetime(ev.get("originalStartTime"))
        self.end = _get_datetime(ev.get("end"))
        self.summary = ev.get("summary")
        self.organizer = ev.get("organizer", {}).get("email")
        self.description = ev.get("description")
        self.status = ev.get("status")
        self.createdBy = ev.get("creator", {}).get("email")
        self.created = dt_util.get_datetime(ev.get("created")) if "created" in ev else None
        self.updated = dt_util.get_datetime(ev.get("updated")) if "updated" in ev else None
        self.providerId = ev["id"]
        self.transparency = ev.get("transparency")
        self.recurrence = ev.get("recurrence")
        self.isRecurring = ev.get("recurrence") is not None
        self.id = self.generate_id()
        self.createdAt = utc_now
        self.updatedAt = utc_now

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
    def summary(self):
        return self._summary

    @summary.setter
    def summary(self, value):
        self._summary = value

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
        return self._attendees if self._attendees else []

    @attendees.setter
    def attendees(self, value):
        self._attendees = value

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value

    @property
    def attachments(self):
        return self._attachments if self._attachments else []

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
    def providerId(self):
        return self._provider_id

    @providerId.setter
    def providerId(self, value):
        self._provider_id = value

    @property
    def createdBy(self):
        return self._created_by

    @createdBy.setter
    def createdBy(self, value):
        self._created_by = value

    @property
    def created(self):
        return self._created

    @created.setter
    def created(self, value):
        self._created = value

    @property
    def updated(self):
        return self._updated

    @updated.setter
    def updated(self, value):
        self._updated = value

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


class RecurringExceptionEvent(Event):
    _collection = 'recurring_exception_events'

    _recurring_event_provider_id = None

    def generate_id(self):
        # Converts original start time into utc and calculates unix timestamp
        unix_milli_timestamp = str(int(self.originalStart.astimezone(tz=datetime.timezone.utc).timestamp() * 1000))
        return self._recurring_event_provider_id + '__' + unix_milli_timestamp

    # Properties

    @property
    def recurringEventProviderId(self):
        return self._recurring_event_provider_id

    @recurringEventProviderId.setter
    def recurringEventProviderId(self, value):
        self._recurring_event_provider_id = value
