import logging

from flask import Blueprint

logger = logging.getLogger(__name__)
api = Blueprint('signin', __name__, url_prefix='/api/v1/signin')
