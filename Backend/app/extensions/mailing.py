import os
import base64
import pickle
import logging

from email.mime.text import MIMEText

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)


class MailingService:
    service = None
    sender = "imyuvarajselvam@gmail.com"

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        credentials = None
        if os.path.exists('app/resources/token.pickle'):
            with open('app/resources/token.pickle', 'rb') as token:
                credentials = pickle.load(token)
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                CLIENT_CONFIG = app.config.get('GMAIL_CLIENT_CONFIG_PATH')
                GMAIL_SCOPES = ['https://mail.google.com/']
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_CONFIG, GMAIL_SCOPES)
                credentials = flow.run_local_server(port=0)
            with open('app/resources/token.pickle', 'wb') as token:
                pickle.dump(credentials, token)
        self.service = build('gmail', 'v1', credentials=credentials)

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
