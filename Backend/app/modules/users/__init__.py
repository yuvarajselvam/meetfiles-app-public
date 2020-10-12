from app.extensions import api


def init_app(app):
    from . import resources
    api.add_namespace(resources.api)
