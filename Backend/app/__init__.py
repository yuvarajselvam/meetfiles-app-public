from flask import Flask

app = Flask(__name__)
app.config.from_object('config.LocalConfig')


def create_app():
    from . import extensions
    extensions.init_app(app)

    from .api.signin import api as signin
    app.register_blueprint(signin)
    return app
