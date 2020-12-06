from datetime import datetime

from app.models.base.entity import Entity


class CalendarBase(Entity):
    _collection = 'calendars'
    _resource_prefix = 'CAL'
    _required_fields = ["provider"]

    def __init__(self,
                 user: str = None,
                 provider: str = None,
                 providerId: str = None,
                 syncToken: str = None,
                 notifChannel: dict = None,
                 lastSyncedAt: datetime = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._service = None
        self._account = None  # Account object - will be used for getting creds
        self.user = user
        self.provider = provider
        self.providerId = providerId
        self.syncToken = syncToken
        self.notifChannel = notifChannel or dict()
        self.lastSyncedAt = lastSyncedAt

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, value):
        self._user = value

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
    def notifChannel(self):
        return self._notif_channel

    @notifChannel.setter
    def notifChannel(self, value):
        self._notif_channel = value

    @property
    def syncToken(self):
        return self._sync_token

    @syncToken.setter
    def syncToken(self, value):
        self._sync_token = value

    @property
    def lastSyncedAt(self):
        return self._last_synced_at

    @lastSyncedAt.setter
    def lastSyncedAt(self, value):
        self._last_synced_at = value
