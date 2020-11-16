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

    def add_event(self, event: Event):
        if self.provider == "google":
            self.create_google_event(event)
        elif self.provider == "microsoft":
            self.create_microsoft_event(event)
        event.save()

    def create_google_event(self, event: Event):
        pass

    def create_microsoft_event(self, event: Event):
        pass

    def sync_events(self):
        if self.provider == "google":
            events = self.fetch_google_events()
            print(events)
            print(Event.sync_google_events(events, self._account))
        elif self.provider == "microsoft":
            events = self.fetch_microsoft_events()
            print(events)
            print(Event.sync_microsoft_events(events, self._account))

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
        self.lastSyncedAt = datetime.utcnow()
        self.save()
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
