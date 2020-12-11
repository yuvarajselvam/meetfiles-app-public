from flask_session import Session
from flask_login import LoginManager
from flask_paranoid import Paranoid

from .db import MongoDB
from .logging import Logger
from .mailing import MailingService
from .firebase import FirebaseService
from .after_response import AfterResponse

db = MongoDB()
logger = Logger()
session = Session()
paranoid = Paranoid()
login_manager = LoginManager()
mailer = MailingService()
firebase_service = FirebaseService()
after_response = AfterResponse()


def init_app(app):
    for extension in (logger,
                      db,
                      session,
                      login_manager,
                      mailer,
                      firebase_service,
                      after_response):
        extension.init_app(app)
