from app.models.base.entity import Entity


class NotificationBase(Entity):
    _collection = 'notifications'
    _resource_prefix = 'NTF'
    _required_fields = []

    def __init__(self,
                 title: str = None,
                 body: str = None,
                 isRead: bool = False,
                 user: str = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.body = body
        self.isRead = isRead
        self.user = user
        
    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, value):
        self._body = value

    @property
    def isRead(self):
        return self._is_read

    @isRead.setter
    def isRead(self, value):
        self._is_read = value

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, value):
        self._user = value
