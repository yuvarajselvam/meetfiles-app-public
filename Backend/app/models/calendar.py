import time
import uuid
import logging

from urllib import parse
from datetime import datetime

import requests

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError as GoogleHttpError

from app.models.event import Event
from app.models.base.calendar_base import CalendarBase
from app.models.base.event_base import VideoConferenceType

logger = logging.getLogger(__name__)


class Calendar(CalendarBase):
    CALENDAR_MAX_END = "2050-12-31 23:59:59.999Z"

    def get_service(self):
        if not self._service:
            if self.provider == "google":
                self._service = self.get_google_service()
            elif self.provider == "microsoft":
                self._service = self.get_microsoft_service()
        return self._service

    def get_google_service(self):
        if not self._account:
            raise AssertionError("Account not set for Calendar object.")
        creds = self._account.get_credentials()
        return build('calendar', 'v3', credentials=creds)

    def get_microsoft_service(self):
        return self._account.get_service()

    def add_event(self, event: Event, follow_up=None, video_conf_type=None):
        if self.provider == "google":
            self.add_google_event(event, video_conf_type)
        elif self.provider == "microsoft":
            self.add_microsoft_event(event, video_conf_type)
        if follow_up:
            event.followUpEvent = follow_up.id
            follow_up.add_event(event)
            follow_up.save()
        event.save()
        return event

    def add_google_event(self, event: Event, video_conf_type=None):
        def _get_conf_data_req_obj():
            return {"createRequest": {"conferenceSolutionKey": {"type": "hangoutsMeet"}, "requestId": uuid.uuid4().hex}}

        def _wait_till_conf_create(_ev):
            _status = _ev.get("conferenceData", {}).get("createRequest", {}).get("status", None)
            if _status and _status["statusCode"] == "pending":
                wait_time = 0
                multiplier = 1
                while _status and _status["statusCode"] == "pending":
                    wait_time += (.5 * multiplier)
                    time.sleep(wait_time)
                    _ev = service.events().get(calendarId='primary', eventId=ev.get("id")).execute()
                    _status = ev.get("conferenceData", {}).get("createRequest", {}).get("status", None)
                    multiplier += 1
            return _ev

        service = self.get_service()
        google_event = event.to_google_event()
        if video_conf_type == VideoConferenceType.GOOGLE_MEET.value:
            google_event["conferenceData"] = _get_conf_data_req_obj()
        try:
            ev = service.events() \
                .insert(calendarId='primary', body=google_event, conferenceDataVersion=1) \
                .execute()
            if video_conf_type == VideoConferenceType.GOOGLE_MEET.value:
                ev = _wait_till_conf_create(ev)
                status = ev.get("conferenceData", {}).get("createRequest", {}).get("status", None)
                if status and status == "failure":
                    body = {"conferenceData": _get_conf_data_req_obj()}
                    ev = service.events() \
                        .patch(calendarId='primary', eventId=ev.get("id"), body=body, conferenceDataVersion=1) \
                        .execute()
                    ev = _wait_till_conf_create(ev)
                    status = ev.get("conferenceData", {}).get("createRequest", {}).get("status", None)
                    if status and status == "failure":
                        raise NotImplementedError
            event.from_google_event(ev)
        except GoogleHttpError as e:
            logger.error(e.resp, e.content, e.error_details)
            return

    def add_microsoft_event(self, event, video_conf_type=None):
        service = self.get_service()
        microsoft_event = event.to_microsoft_event()
        url = "https://graph.microsoft.com/v1.0/me/events"
        result = service.post(url, data=microsoft_event)
        try:
            result.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(str(e))
            return
        event.from_microsoft_event(result)

    def edit_event(self, event, keys=None):
        if self.provider == "google":
            self.edit_google_event(event, keys)
        elif self.provider == "microsoft":
            self.edit_microsoft_event(event, keys)
        event.save()

    def edit_google_event(self, event, keys=None):
        service = self.get_service()
        google_event = event.to_google_event(keys)
        ev = None
        try:
            ev = service.events() \
                .patch(calendarId='primary', eventId=event.providerId,
                       body=google_event, conferenceDataVersion=1) \
                .execute()
        except GoogleHttpError as e:
            logger.error(e.resp, e.content, e.error_details)
            return
        if ev:
            event.from_google_event(ev)

    def edit_microsoft_event(self, event, keys=None):
        service = self.get_service()
        microsoft_event = event.to_microsoft_event(keys)
        url = f"https://graph.microsoft.com/v1.0/me/events/{event.providerId}"
        result = service.patch(url, data=microsoft_event)
        try:
            result.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(str(e))
            return
        event.from_microsoft_event(result)

    def rsvp_to_event(self, event, response):
        if self.provider == "google":
            self.rsvp_to_google_event(event, response)
        elif self.provider == "microsoft":
            self.rsvp_to_microsoft_event(event, response)

    def rsvp_to_google_event(self, event, response):
        attendees = []
        for attendee in event.attendees.copy():
            if attendee["email"] == self._account.email:
                attendee["responseStatus"] = response
            attendees.append(attendee)
        event.attendees = attendees
        self.edit_event(event, keys="attendees")

    def rsvp_to_microsoft_event(self, event, response):
        service = self.get_service()
        response_endpoint_map = {"accepted": "accept", "declined": "decline",
                                 "tentative": "tentativelyAccept"}
        endpoint = response_endpoint_map[response]
        url = f"https://graph.microsoft.com/v1.0/me/events/{event.providerId}/{endpoint}"
        result = service.post(url, data={})
        try:
            result.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(str(e))
            return
        attendees = []
        for attendee in event.attendees.copy():
            if attendee["email"] == self._account.email:
                attendee["responseStatus"] = response
            attendees.append(attendee)
        event.attendees = attendees
        event.save()

    def delete_event(self, event):
        if self.provider == "google":
            self.delete_google_event(event)
        elif self.provider == "microsoft":
            self.delete_microsoft_event(event)

    def delete_google_event(self, event):
        service = self.get_service()
        try:
            service.events() \
                .delete(calendarId='primary', eventId=event.providerId) \
                .execute()
        except GoogleHttpError as e:
            logger.error(e.resp, e.content, e.error_details)
            return
        event.isDeleted = True
        event.status = Event.Status.CANCELLED.value
        event.save()

    def delete_microsoft_event(self, event):
        pass

    def watch(self):
        if self.provider == "google":
            self.watch_google_calendar()
        elif self.provider == "microsoft":
            self.watch_microsoft_calendar()

    def watch_google_calendar(self):
        service = self.get_service()

        if self.notifChannel:
            body = {"id": self.notifChannel["id"],
                    "resourceId": self.notifChannel["resourceId"]}
            try:
                service.channels().stop(body=body).execute()
                self.notifChannel = dict()
            except GoogleHttpError as e:
                logger.error(f"Error when stopping notif channel: {str(e)}")

        user_id = self._account.get_user_id()
        body = {"id": "", "type": "web_hook", "address": "", "token": user_id}
        request = service.events().watch(calendarId="primary", body=body)
        try:
            result = request.execute()
            self.notifChannel = result
        except GoogleHttpError as e:
            logger.error(f"Error when stopping notif channel: {str(e)}")
        self.save()

    def watch_microsoft_calendar(self):
        pass

    def sync_events(self):
        from app.models.meetsection import Meetsection
        changed_meetsections = []
        if self.provider == "google":
            events = self.fetch_google_events()
            changed_meetsections = Event.sync_google_events(events, self._account)
        elif self.provider == "microsoft":
            events = self.fetch_microsoft_events()
            changed_meetsections = Event.sync_microsoft_events(events, self._account)
        self.lastSyncedAt = datetime.utcnow()
        if changed_meetsections:
            Meetsection.bulk_update_firebase(list(changed_meetsections), self._account.get_user())
        self.save()

    def fetch_google_events(self):
        service = self.get_service()
        sync_token = self.syncToken
        now = datetime.utcnow().isoformat() + 'Z' if not sync_token else None
        events = []
        page_token = None
        while True:
            params = {"calendarId": "primary", "pageToken": page_token,
                      "syncToken": sync_token, "timeMin": now}
            request = service.events().list(**params)
            try:
                result = request.execute()
            except GoogleHttpError as e:
                if not e.resp.status == 410:
                    raise
                params.pop("syncToken", None)
                params["timeMin"] = self._account.get_user().createdAt
                result = service.events().list(**params).execute()
            page_token = result.get('nextPageToken')
            events += result.get('items')
            if not page_token:
                sync_token = result.get('nextSyncToken')
                break
        self.syncToken = sync_token
        return events

    def fetch_microsoft_events(self):
        service = self.get_service()
        graph_url = 'https://graph.microsoft.com/v1.0'
        sync_token = self.syncToken
        now = datetime.utcnow().isoformat() + 'Z' if not sync_token else None
        end = self.CALENDAR_MAX_END if not sync_token else None
        events = []
        page_token = None
        while True:
            params = {"StartDateTime": now, "EndDateTime": end,
                      "$deltatoken": sync_token, "$skiptoken": page_token}
            headers = {"Prefer": "odata.maxpagesize=50"}
            result = service.get(f"{graph_url}/me/calendarView/delta", params=params, headers=headers)
            try:
                result.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if not e.response.status_code == 410:
                    raise
                params = {"StartDateTime": self._account.get_user().createdAt, "EndDateTime": end}
                result = service.get(f"{graph_url}/me/calendarView/delta", params=params, headers=headers)
                result.raise_for_status()
            result = result.json()
            events += result.get('value')
            next_link = result.get('@odata.nextLink')
            if not next_link:
                delta_link = result.get('@odata.deltaLink')
                sync_token = parse.parse_qs(parse.urlparse(delta_link).query).get('$deltatoken')[0]
                break
            page_token = parse.parse_qs(parse.urlparse(next_link).query).get('$skiptoken')[0]
            sync_token = None
        self.syncToken = sync_token
        self.lastSyncedAt = datetime.utcnow()
        self.save()
        return events
