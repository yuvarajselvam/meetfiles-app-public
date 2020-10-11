import os
import logging

from flask import Flask
from dotenv import load_dotenv

load_dotenv('.env')
app = Flask(__name__)


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
