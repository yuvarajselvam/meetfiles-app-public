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

    def add_event(self, event: Event, video_conf_type=None):
        if self.provider == "google":
            self.add_google_event(event, video_conf_type)
        elif self.provider == "microsoft":
            pass
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
        if video_conf_type == "meet":
            google_event["conferenceData"] = _get_conf_data_req_obj()
        print(google_event)
        try:
            ev = service.events() \
                .insert(calendarId='primary', body=google_event, conferenceDataVersion=1) \
                .execute()
            print(ev)
            if video_conf_type == "meet":
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
            print(e.resp, e.content, e.error_details)
            raise

    def sync_events(self):
        if self.provider == "google":
            events = self.fetch_google_events()
            print(events)
            print(Event.sync_google_events(events, self._account))
        elif self.provider == "microsoft":
            events = self.fetch_microsoft_events()
            print(events)
            print(Event.sync_microsoft_events(events, self._account))
        self.lastSyncedAt = datetime.utcnow()
        self.save()

    def fetch_google_events(self):
        print("Fetching google events")
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
            except GoogleHttpError:
                return  # TODO: Handle Sync Token Invalidation: e.resp.status == 410
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
            result = service.get(f"{graph_url}/me/calendarView/delta",
                                 params=params, headers=headers)
            try:
                result.raise_for_status()
            except requests.exceptions.HTTPError:
                logger.debug(f"Http Error - {result.json()}")
                return  # TODO: Handle Sync Token Invalidation: e.resp.status == 410
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
