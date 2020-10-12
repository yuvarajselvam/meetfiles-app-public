from flask import Blueprint
from flask_restplus import Api

from .db import MongoDB
from .logging import Logger

logger = Logger()
db = MongoDB()

blueprint = Blueprint('api_v1', __name__, url_prefix="api/v1")
api = Api(blueprint)


def init_app(app):
    for extension in (logger, db, api):
        extension.init_app(app)
