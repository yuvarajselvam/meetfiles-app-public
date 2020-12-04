import datetime

from pymongo.operations import UpdateOne

from app.models.base.event_base import EventBase
from app.utils.datetime import get_start_times, get_datetime, get_rrule_from_pattern

GOOGLE_RESPONSE_STATUS_MAP = {'accepted': 'accepted', 'needsAction': 'none',
                              'declined': 'declined', 'tentative': 'tentative'}


class Event(EventBase):
    @classmethod
    def sync_google_events(cls, events, account):
        from app.models.meetsection import Meetsection
        user = account.get_user_id()
        default_meetsection = Meetsection.get_default(account.email).id
        provider_ids = [ev["id"] for ev in events]
        _events = cls.find({"user": user, "providerId": {"$in": provider_ids}})
        changed_meetsections = set()
        if events:
            bulk_write_data = {"events": [], "recurring_exception_events": []}
            REE = RecurringExceptionEvent
            for ev in events:
                e_obj = list(filter(lambda e: e["providerId"] == ev["id"], _events))
                meetsection = e_obj[0]["meetsection"] if e_obj else default_meetsection
                changed_meetsections.add(meetsection)
                recurring_event_id = ev.get("recurringEventId")
                params = {"meetsection": meetsection, "user": user}
                event = Event(**params) if not recurring_event_id else REE(**params)
                event.recurringEventProviderId = recurring_event_id
                event.from_google_event(ev)
                operation = UpdateOne({"providerId": event.providerId, "user": account.get_user_id()},
                                      {"$set": event.json()}, upsert=True)
                bulk_write_data[event._collection].append(operation)
            Event.bulk_write(bulk_write_data['events'])
            REE.bulk_write(bulk_write_data['recurring_exception_events'])
        return changed_meetsections

    def from_google_event(self, ev):
        utc_now = datetime.datetime.utcnow()
        attendees = ev.get("attendees", [])
        for attendee in attendees:
            is_resource = attendee.get("resource")
            if is_resource:
                continue
            response = attendee.get("responseStatus")
            response = GOOGLE_RESPONSE_STATUS_MAP[response]
            self.attendees.append({
                "email": attendee.get("email"),
                "responseStatus": response,
                "optional": attendee.get("optional", False)
            })
        attachments = ev.get("attachments")
        self.attachments = []
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
        self.title = ev.get("summary")
        self.organizer = ev.get("organizer", {}).get("email")
        self.location = ev.get("location")
        if ev.get("start"):
            self.isAllDay = "date" in ev.get("start")
        self.description = ev.get("description")
        self.conferenceData = ev.get("conferenceData")
        self.status = ev.get("status")
        self.created = ev.get("created")
        self.updated = ev.get("updated")
        self.provider = "google"
        self.providerId = ev["id"]
        self.transparency = ev.get("transparency")
        self.webLink = ev.get("htmlLink")
        self.recurrence = ev.get("recurrence")
        self.isRecurring = ev.get("recurrence") is not None
        self.id = self.generate_id()
        self.createdAt = utc_now
        self.updatedAt = utc_now

    def to_google_event(self, keys=None):
        google_object = {
            "summary": self.title,
            "start": {"date" if self.isAllDay else "dateTime": self.start.isoformat()},
            "end": {"date" if self.isAllDay else "dateTime": self.end.isoformat()},
            "location": self.location,
            "description": self.description
        }
        inverse_status_map = {value: key for key, value in GOOGLE_RESPONSE_STATUS_MAP.items()}
        attendees = []
        for attendee in self.attendees:
            _attendee = {"email": attendee["email"]}
            response = attendee.get("responseStatus")
            if response:
                _attendee["responseStatus"] = inverse_status_map[response]
            attendees.append(_attendee)
        google_object["attendees"] = attendees if attendees else None
        if keys:
            [google_object.pop(k, None) for k in keys]
        return google_object

    @classmethod
    def sync_microsoft_events(cls, events, account):
        from app.models.meetsection import Meetsection
        user = account.get_user_id()
        service = account.get_service()
        default_meetsection = Meetsection.get_default(account.email).id
        provider_ids = [ev["id"] for ev in events]
        _events = cls.find({"user": user, "providerId": {"$in": provider_ids}})
        changed_meetsections = set()
        if events:
            bulk_write_data = {"events": [], "recurring_exception_events": []}
            REE = RecurringExceptionEvent
            for ev in events:
                if not ev.get("type") == "occurrence":
                    e_obj = list(filter(lambda e: e["providerId"] == ev["id"], _events))
                    meetsection = e_obj[0]["meetsection"] if e_obj else default_meetsection
                    changed_meetsections.add(meetsection)
                    recurring_event_id = ev.get("seriesMasterId")
                    params = {"meetsection": meetsection, "user": user}
                    event = Event(**params) if not recurring_event_id else REE(**params)
                    event.recurringEventProviderId = recurring_event_id
                    if ev.get("@removed"):
                        event.isDeleted = True
                    else:
                        event.from_microsoft_event(ev, service)
                    operation = UpdateOne({"providerId": event.providerId, "user": user},
                                          {"$set": event.json()}, upsert=True)
                    bulk_write_data[event._collection].append(operation)
            Event.bulk_write(bulk_write_data['events'])
            REE.bulk_write(bulk_write_data['recurring_exception_events'])
        return changed_meetsections

    def from_microsoft_event(self, ev, service):
        utc_now = datetime.datetime.utcnow()
        attendees = ev.get("attendees", [])
        self.attendees = []
        for attendee in attendees:
            attendee_type = attendee.get("type")
            if (not attendee_type) or attendee_type == "resource":
                continue
            response = attendee.get("status", {}).get("response")
            response = "none" if response == "notresponded" else response
            response = "tentative" if response == "tentativelyaccepted" else response
            response = "accepted" if response == "organizer" else response
            self.attendees.append({
                "email": attendee.get("emailAddress", {}).get("address"),
                "responseStatus": response,
                "optional": attendee_type == "optional"
            })
        has_attachments = ev.get("hasAttachments")
        self.attachments = []
        if has_attachments:
            attachments = service.fetch_event_attachments(ev["id"])['value']
            for attachment in attachments:
                self.attachments.append({
                    "id": attachment.get("id"),
                    "url": attachment.get("fileUrl"),
                    "type": attachment.get("contentType"),
                    "external": True
                })

        self.start = _get_datetime(ev.get("start"))
        self.originalStart = ev.get("originalStart")
        self.end = _get_datetime(ev.get("end"))
        self.title = ev.get("subject")
        self.organizer = ev.get("organizer", {}).get("emailAddress", {}).get("address")
        self.location = ev.get("location", {}).get("displayName")
        self.isAllDay = ev.get("isAllDay")
        self.description = ev.get("body", {}).get("content")
        self.status = "cancelled" if ev.get("isCancelled") else "confirmed"
        self.created = ev.get("createdDateTime")
        self.updated = ev.get("lastModifiedDateTime")
        self.provider = "microsoft"
        self.providerId = ev["id"]
        self.webLink = ev.get("webLink")
        rp = ev.get("recurrence")
        self.recurrence = get_rrule_from_pattern(rp)
        self.isRecurring = rp is not None
        self.id = self.generate_id()
        self.createdAt = utc_now
        self.updatedAt = utc_now

    def to_microsoft_event(self):
        microsoft_object = {
            "subject": self.title,
            "body": {
                "contentType": "HTML",
                "content": self.description
            },
            "start": {"dateTime": self.start.isoformat()},
            "end": {"dateTime": self.end.isoformat()},
            "location": {"displayName": self.location},
        }
        attendees = []
        for attendee in self.attendees:
            attendees.append({"email": attendee["email"]})
        microsoft_object["attendees"] = attendees if attendees else None
        return microsoft_object

    def expand(self, past=False):
        if not self.isRecurring:
            raise ValueError("Tried to expand non recurring event")

        start = self.start if past else datetime.datetime.utcnow()
        start_times = get_start_times(self.recurrence, start=start)
        instances = []
        query = {"recurringEventProviderId": self.providerId, "user": self.user}
        exceptions = RecurringExceptionEvent.find(query)
        clone = self.to_simple_object()
        duration = self.end - self.start
        for st in start_times:
            instance = self._get_instance_from_event(st, duration, exceptions, clone)
            instances.append(instance)
        return instances

    def _get_instance_from_event(self, start, duration, exceptions, clone):
        REE = RecurringExceptionEvent
        ree = REE(recurringEventProviderId=self.providerId, originalStart=self.start)
        exception = list(filter(lambda o: o["id"] == ree.generate_id(), exceptions))
        if exception:
            instance = REE(**exception[0]).to_simple_object()
        else:
            instance = clone.copy()
            instance["start"] = start,
            instance["end"] = start + duration
        return instance

    def next_start_end_in_series(self):
        utc_now = datetime.datetime.utcnow()
        start_times = get_start_times(self.recurrence, start=utc_now)
        duration = self.end - self.start
        if start_times:
            return start_times[0], start_times[0] + duration
        else:
            return None, None

    def to_simple_object(self):
        ev = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
        }
        from app.models.user import User
        users = User.find({"accounts.email": {"$in": [a["email"] for a in self.attendees]}})
        attendees = []
        for _attendee in self.attendees:
            email = _attendee["email"]
            attendee = {"email": email, "type": "organizer" if email == self.organizer else None}
            _user = list(filter(lambda u: u["accounts"][0]["email"] == email, users))
            if _user:
                attendee["displayName"] = _user[0]["accounts"][0]["name"]
            attendees.append(attendee)
        if self.recurrence:
            ev["recurrence"] = {
                "rule": "\n".join(self.recurrence),
                "recurrenceText": self.recurrenceText
            }
            if self.recurrenceEnd:
                ev["recurrence"]["recurrenceEnd"] = self.recurrenceEnd.isoformat()
        ev["attendees"] = attendees if attendees else None
        start = {"date": self.start.strftime("%Y-%m-%d"),
                 "time": self.start.strftime("%I:%M %p")}
        end = {"date": self.end.strftime("%Y-%m-%d"),
               "time": self.end.strftime("%I:%M %p")}
        ev["start"] = start
        ev["end"] = end
        return ev

    @classmethod
    def fetch_by_date_range(cls, start, end):
        query = {"start": {"$gte": get_datetime(start), "$lt": get_datetime(end)}}
        events = cls.find(query)
        return [cls(**ev).to_simple_object() for ev in events]


class RecurringExceptionEvent(Event):
    _collection = 'recurring_exception_events'

    def __init__(self, recurringEventProviderId: str = None, *args, **kwargs):
        self.recurringEventProviderId = recurringEventProviderId
        super().__init__(*args, **kwargs)

    def generate_id(self):
        # Converts original start time into utc and calculates unix timestamp
        original_start_utc = self.originalStart.astimezone(tz=datetime.timezone.utc)
        unix_milli_timestamp = str(int(original_start_utc.timestamp() * 1000))
        master_id = self._recurring_event_provider_id
        master_id = master_id.split('_')[0]
        return master_id + '_' + unix_milli_timestamp

    # Properties

    @property
    def recurringEventProviderId(self):
        return self._recurring_event_provider_id

    @recurringEventProviderId.setter
    def recurringEventProviderId(self, value):
        self._recurring_event_provider_id = value


def _get_datetime(obj):
    if obj and "dateTime" in obj:
        return [obj["dateTime"], obj.get("timeZone")]
    elif obj and "date" in obj:
        return [obj["date"], obj.get("timeZone")]
