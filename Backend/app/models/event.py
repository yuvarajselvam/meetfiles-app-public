import datetime

from pymongo.operations import UpdateOne

from app.models.followup import FollowUp
from app.models.base.event_base import EventBase
from app.utils.datetime import get_start_times, get_datetime, get_rrule_from_pattern

GOOGLE_RESPONSE_STATUS_MAP = {'accepted': 'accepted', 'needsAction': 'none',
                              'declined': 'declined', 'tentative': 'tentative'}

MICROSOFT_RESPONSE_STATUS_MAP = {'none': 'none', 'tentativelyAccepted': 'tentative',
                                 'organizer': 'accepted', 'accepted': 'accepted',
                                 'declined': 'declined', 'notResponded': 'none'}


class Event(EventBase):
    @classmethod
    def sync_google_events(cls, events, account):
        user = account.get_user_id()
        provider_ids = [ev["id"] for ev in events]
        _events = cls.find({"providerId": {"$in": provider_ids}})
        changed_meetsections = set()
        if events:
            bulk_write_data = {"events": [], "recurring_exception_events": []}
            REE = RecurringExceptionEvent
            for ev in events:
                from app.models.meetsection import Meetsection
                default = Meetsection.get_default(account.email).id
                e_obj = list(filter(lambda e: e["providerId"] == ev["id"], _events))
                # TODO: Use ETag to verify if event is not already updated
                if e_obj:
                    _meetsections = e_obj[0]["meetsections"]
                    meetsections = _meetsections
                    if not list(filter(lambda m: m["user"] == user, _meetsections)):
                        meetsections.append({"id": default, "user": user})
                else:
                    meetsections = [{"id": default, "user": user}]
                recurring_event_id = ev.get("recurringEventId")
                params = {"meetsections": meetsections}
                event = Event(**params) if not recurring_event_id else REE(**params)
                event.recurringEventProviderId = recurring_event_id
                event.from_google_event(ev)
                operation = UpdateOne({"providerId": event.providerId},
                                      {"$set": event.json()}, upsert=True)
                bulk_write_data[event._collection].append(operation)
                changed_meetsections |= set([m["id"] for m in meetsections])
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
        if not self.id:
            self.id = self.generate_id()
            self.createdAt = utc_now
        self.updatedAt = utc_now

    def to_google_event(self, keys=None):
        google_object = {
            "summary": self.title,
            "start": {"date" if self.isAllDay else "dateTime": self.start.strftime('%Y-%m-%dT%H:%M:%SZ')},
            "end": {"date" if self.isAllDay else "dateTime": self.end.strftime('%Y-%m-%dT%H:%M:%SZ')},
            "recurrence": self.recurrence,
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
            [google_object.pop(k, None) for k in google_object.copy() if k not in keys]
        return google_object

    @classmethod
    def sync_microsoft_events(cls, events, account):
        service = account.get_service()
        user = account.get_user_id()
        provider_ids = [ev["id"] for ev in events]
        _events = cls.find({"providerId": {"$in": provider_ids}})
        changed_meetsections = set()
        if events:
            bulk_write_data = {"events": [], "recurring_exception_events": []}
            REE = RecurringExceptionEvent
            for ev in events:
                if ev.get("type") == "occurrence":
                    continue
                meetsections = []
                e_obj = list(filter(lambda e: e["providerId"] == ev["id"], _events))
                if e_obj:
                    _meetsections = e_obj[0]["meetsections"]
                    meetsections = list(filter(lambda m: m["user"] == user, _meetsections))
                if not meetsections:
                    from app.models.meetsection import Meetsection
                    default = Meetsection.get_default(account.email).id
                    meetsections = [{"id": default, "user": user}]
                recurring_event_id = ev.get("seriesMasterId")
                params = {"meetsections": meetsections}
                event = Event(**params) if not recurring_event_id else REE(**params)
                event.recurringEventProviderId = recurring_event_id
                if ev.get("@removed"):
                    event.isDeleted = True
                else:
                    event.from_microsoft_event(ev, service)
                operation = UpdateOne({"providerId": event.providerId},
                                      {"$set": event.json()}, upsert=True)
                changed_meetsections |= set([m["id"] for m in meetsections])
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
            response = MICROSOFT_RESPONSE_STATUS_MAP[response]
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
        if not self.id:
            self.id = self.generate_id()
            self.createdAt = utc_now
        self.updatedAt = utc_now

    def to_microsoft_event(self, keys=None):
        microsoft_object = {
            "subject": self.title,
            "body": {
                "contentType": "HTML",
                "content": self.description
            },
            "start": {"dateTime": self.start.strftime('%Y-%m-%dT%H:%M:%SZ')},
            "end": {"dateTime": self.end.strftime('%Y-%m-%dT%H:%M:%SZ')},
            "location": {"displayName": self.location},
        }
        attendees = []
        for attendee in self.attendees:
            attendees.append({"email": attendee["email"]})
        microsoft_object["attendees"] = attendees if attendees else None
        if keys:
            [microsoft_object.pop(k, None) for k in microsoft_object.copy() if k not in keys]
        return microsoft_object

    def expand(self, end=None, calendar=False):
        if not self.isRecurring:
            raise ValueError("Tried to expand non recurring event")

        start_times = get_start_times(self.recurrence, self.start, get_datetime(end))
        instances = []
        query = {
            "recurringEventProviderId": self.providerId,
            "status": {"$ne": "cancelled"},
            "$or": [{"isDeleted": {"$exists": False}}, {"isDeleted": False}]
        }
        exceptions = RecurringExceptionEvent.find(query)
        clone = self.to_simple_object() if not calendar else self.to_calendar_object()
        duration = self.end - self.start
        for st in start_times:
            instance = self._get_instance_from_event(st, duration, exceptions, clone, calendar=calendar)
            instances.append(instance)
        return instances

    def _get_instance_from_event(self, start, duration, exceptions, clone, calendar=False):
        REE = RecurringExceptionEvent
        ree = REE(recurringEventProviderId=self.providerId, originalStart=start)
        exception = list(filter(lambda o: o["id"] == ree.generate_id(), exceptions))
        if exception:
            instance_obj = REE(**exception[0])
            if not calendar:
                instance = instance_obj.to_simple_object()
            else:
                instance = instance_obj.to_calendar_object()
        else:
            instance = clone.copy()
            end = start + duration
            if not calendar:
                instance["start"] = {"date": start.strftime("%Y-%m-%d"),
                                     "time": start.strftime("%I:%M %p"),
                                     "utc": start.strftime('%Y-%m-%dT%H:%M:%SZ')}
                instance["end"] = {"date": end.strftime("%Y-%m-%d"),
                                   "time": end.strftime("%I:%M %p"),
                                   "utc": end.strftime('%Y-%m-%dT%H:%M:%SZ')}
            else:
                instance["start"] = start.strftime('%Y-%m-%dT%H:%M:%SZ')
                instance["end"] = end.strftime('%Y-%m-%dT%H:%M:%SZ')
        return instance

    def next_start_end_in_series(self):
        utc_now = datetime.datetime.utcnow()
        start_times = get_start_times(self.recurrence, start=utc_now)
        duration = self.end - self.start
        if start_times:
            return start_times[0], start_times[0] + duration
        else:
            return None, None

    def get_attendees(self):
        from app.models.user import User
        users = User.find({"accounts.email": {"$in": [a["email"] for a in self.attendees]}})
        attendees = []
        for _attendee in self.attendees:
            email = _attendee["email"]
            _attendee["type"] = "organizer" if email == self.organizer else None
            _user = list(filter(lambda u: u["accounts"][0]["email"] == email, users))
            if _user:
                _attendee["displayName"] = _user[0]["accounts"][0]["name"]
                _attendee["imageUrl"] = _user[0]["accounts"][0]["imageUrl"]
            attendees.append(_attendee)
        return attendees if attendees else None

    def to_simple_object(self):
        ev = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "attendees": self.get_attendees()
        }
        if self.recurrence:
            ev["recurrence"] = {
                "rule": "\n".join(self.recurrence),
                "recurrenceText": self.recurrenceText
            }
            if self.recurrenceEnd:
                ev["recurrence"]["recurrenceEnd"] = self.recurrenceEnd.strftime('%Y-%m-%dT%H:%M:%SZ')
        ev["start"] = {"date": self.start.strftime("%Y-%m-%d"),
                       "time": self.start.strftime("%I:%M %p"),
                       "utc": self.start.strftime('%Y-%m-%dT%H:%M:%SZ')}
        ev["end"] = {"date": self.end.strftime("%Y-%m-%d"),
                     "time": self.end.strftime("%I:%M %p"),
                     "utc": self.end.strftime('%Y-%m-%dT%H:%M:%SZ')}
        return ev

    def to_full_object(self):
        from flask_login import current_user
        result = self.to_simple_object()
        if not current_user.is_anonymous():
            meetsection = list(filter(lambda m: m["user"] == current_user.id, self.meetsections))[0]
            result["meetSection"] = {"id": meetsection["id"]}
        if self.isRecurring:
            result["recurringEvents"] = self.expand()
        elif self.followUp:
            follow_up = FollowUp.find_one({"id": self.followUp})
            follow_up_events = self.find({"id": {"$in": follow_up.events}})
            result["followUpEvents"] = [Event(**fe).to_simple_object() for fe in follow_up_events]
        return result

    def to_calendar_object(self):
        if self.isAllDay:
            end = self.end - datetime.timedelta(seconds=1)
        else:
            end = self.end
        return {
            "id": self.id,
            "calendarId": "1",
            "title": self.title,
            "body": self.description,
            "start": self.start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "end": end.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "isAllDay": self.isAllDay,
            "attendees": [a["email"] for a in self.attendees],
            "location": self.location,
            "recurrenceRule": self.recurrenceText,
            "category": "time"
        }

    @classmethod
    def fetch_by_date_range(cls, start, end, user, calendar=False):
        start = get_datetime(start)
        end = get_datetime(end)
        non_recurring_query = {
            "start": {"$gte": start, "$lt": end},
            "isRecurring": False,
            "status": {"$ne": "cancelled"},
            "meetsections.user": user,
            "$or": [{"isDeleted": {"$exists": False}}, {"isDeleted": False}]
        }
        non_recurring_events = cls.find(non_recurring_query)
        if not calendar:
            to_ret = [cls(**ev).to_simple_object() for ev in non_recurring_events]
        else:
            to_ret = [cls(**ev).to_calendar_object() for ev in non_recurring_events]
        recurring_query = {
            "isRecurring": True,
            "status": {"$ne": "cancelled"},
            "$and": [{"$or": [{"recurrenceEnd": {"$exists": False}},
                              {"$and": [{"recurrenceEnd": {"$gte": start}},
                                        {"start": {"$lt": end}}]}]},
                     {"$or": [{"isDeleted": {"$exists": False}},
                              {"isDeleted": False}]}],
            "meetsections.user": user
        }
        recurring_events = cls.find(recurring_query)
        for _e in recurring_events:
            e = cls(**_e)
            expanded = e.expand(end, calendar=calendar)
            if not calendar:
                to_ret += list(filter(lambda i: start <= get_datetime(i["start"]["utc"]) < end, expanded))
            else:
                to_ret += list(filter(lambda i: start <= get_datetime(i["start"]) < end, expanded))
        return to_ret


class RecurringExceptionEvent(Event):
    _collection = 'recurring_exception_events'

    def __init__(self, recurringEventProviderId: str = None, *args, **kwargs):
        self.recurringEventProviderId = recurringEventProviderId
        super().__init__(*args, **kwargs)

    def generate_id(self):
        original_start_utc = self.originalStart.astimezone(datetime.timezone.utc)

        unix_milli_timestamp = str(int(original_start_utc.timestamp() * 1000))
        master_id = self._recurring_event_provider_id
        master_id = master_id.split('_')[0]
        return master_id + '_' + original_start_utc.strftime('%Y%m%dT%H%M%SZ')

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
