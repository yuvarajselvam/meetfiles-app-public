from flask import Flask
from dotenv import load_dotenv


def create_app():
    app = Flask(__name__)
    load_dotenv('.env')

    from . import extensions
    extensions.init_app(app)

    return app
