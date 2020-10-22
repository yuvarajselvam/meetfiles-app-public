import tldextract as tld
from flask import Flask, jsonify, request

app = Flask(__name__)
app.config.from_object('config.LocalConfig')


def create_app():
    from . import extensions
    extensions.init_app(app)

    from . import api
    api.init_app(app)

    @app.before_request
    def extract_subdomain():
        url_obj = tld.extract(request.headers.get('X-Forwarded-Host'))
        request.subdomain = url_obj.subdomain

    @app.route('/api/v1/user/1/123/meetsections')
    def test():
        return jsonify([{'name': "Engineering", 'id': "1"}, {'name': "Product Management", 'id': "2"}])

    return app
