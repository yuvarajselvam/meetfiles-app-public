import base64
import logging

from email.mime.text import MIMEText

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class MailingService:
    service = None
    sender = "yymusicplayer@gmail.com"

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        GOOGLE_API_DEVELOPER_KEY = app.config.get('GOOGLE_API_DEVELOPER_KEY')
        self.service = build('gmail', 'v1', developerKey=GOOGLE_API_DEVELOPER_KEY)

    def create_message(self, to, subject, message_text):
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = self.sender
        message['subject'] = subject
        return {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}

    def send_message(self, to_address, subject, message_text):
        try:
            if not self.service:
                raise ValueError("Mailing service not initialized")
            message = self.create_message(to=to_address, subject=subject, message_text=message_text)
            message = self.service.users().messages().send(userId=self.sender, body=message).execute()
            return bool(message)
        except (HttpError, ValueError) as error:
            logger.error(error)
            return False
