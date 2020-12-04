from os import getenv
import tldextract as tld

from flask_login import current_user
from flask import Flask, request, current_app

app = Flask(__name__)
app.config.from_object('config.LocalConfig')
UNPROTECTED_ROUTES = ['signin']


def create_app():
    from . import extensions
    extensions.init_app(app)

    from . import api
    api.init_app(app)

    @app.before_request
    def before_app_request():
        url_obj = tld.extract(request.headers.get('Host', ''))
        request.subdomain = url_obj.subdomain
        path = request.path.lstrip('/api/v1/').split('/')
        if path[0] not in UNPROTECTED_ROUTES and not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()

    @app.after_request
    def after_app_request(response):
        if (200 <= response.status_code < 400) or response.status_code == 404:
            extensions.logger.log(request, None, response.status_code)
        else:
            extensions.logger.log(request, response)
        return response
    return app
