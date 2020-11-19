import logging

from flask import Blueprint

logger = logging.getLogger(__name__)
api = Blueprint('sync', __name__, url_prefix='/api/v1/sync')
