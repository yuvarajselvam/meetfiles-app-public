import os
import json
import pickle
import base64
import logging

from email.mime.text import MIMEText

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)


class MailingService:
    service = None
    sender = "yymusicplayer@gmail.com"

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        GMAIL_SCOPES = ['https://mail.google.com/']
        PICKLE_PATH = 'app/resources/token.pickle'
        with open(app.config.get('GMAIL_CLIENT_CONFIG_PATH')) as f:
            CLIENT_CONFIG = json.load(f)
        credentials = None
        if os.path.exists(PICKLE_PATH):
            with open(PICKLE_PATH, 'rb') as token:
                credentials = pickle.load(token)
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, GMAIL_SCOPES)
                credentials = flow.run_local_server(port=0)
            with open(PICKLE_PATH, 'wb') as token:
                pickle.dump(credentials, token)
        self.service = build('gmail', 'v1', credentials=credentials)

    def create_message(self, to, subject, message_text):
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = self.sender
        message['subject'] = subject
        logger.debug(f"Email message: {message_text}")
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
