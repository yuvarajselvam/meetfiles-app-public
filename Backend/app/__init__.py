from flask import Flask

app = Flask(__name__)
app.config.from_object('config.LocalConfig')


def create_app():
    from . import extensions
    extensions.init_app(app)

    from . import api
    api.init_app(app)

    return app
