import logging

from flask_restplus import Namespace, Resource

from app.extensions import api

logger = logging.getLogger(__name__)
api = Namespace('users', description="Users")


@api.route('/')
class Users(Resource):
    """
    Manipulations with users.
    """
    @staticmethod
    def get(args):
        """
        List of users.
        Returns a list of users starting from ``offset`` limited by ``limit``
        parameter.
        """
        return "Hello"