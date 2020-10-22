from os import path, getenv
from dotenv import load_dotenv

from pymongo import MongoClient

basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, '.env'))


class Config:
    SECRET_KEY = getenv('SECRET_KEY')
    SESSION_TYPE = getenv('SESSION_TYPE')
    SESSION_PERMANENT = getenv('SESSION_PERMANENT')
    SESSION_PROTECTION = getenv('SESSION_PROTECTION')
    SESSION_COOKIE_NAME = getenv('SESSION_COOKIE_NAME')
    SESSION_COOKIE_DOMAIN = getenv('SESSION_COOKIE_DOMAIN')
    SESSION_COOKIE_SECURE = getenv('SESSION_COOKIE_SECURE')
    SESSION_COOKIE_SAMESITE = getenv('SESSION_COOKIE_SAMESITE')
    PERMANENT_SESSION_LIFETIME = int(getenv('PERMANENT_SESSION_LIFETIME'))

    GOOGLE_CLIENT_ID = getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = getenv('GOOGLE_CLIENT_SECRET')
    AZURE_CLIENT_ID = getenv('AZURE_CLIENT_ID')
    AZURE_CLIENT_SECRET = getenv('AZURE_CLIENT_SECRET')


class LocalConfig(Config):
    APP_URL = getenv('APP_URL')
    BASE_URL = getenv('BASE_URL')
    MONGODB_URI = getenv('DEV_MONGODB_URI')
    MONGODB_DB = getenv('DEV_MONGODB_DB')
    SESSION_MONGODB = MongoClient(MONGODB_URI)
    SESSION_MONGODB_DB = MONGODB_DB
    SESSION_COOKIE_SECURE = False
    OAUTHLIB_INSECURE_TRANSPORT = 1
