import os
import jwt
import datetime
from flask import jsonify


def make_response(response_tuple):
    (message, code) = response_tuple
    response = jsonify(message=message)
    response.status_code = code
    return response


def generate_auth_token_response(userId):
    exp = datetime.datetime.utcnow() + datetime.timedelta(days=30)
    payload = {"userId": userId, "exp": exp}
    auth_token = jwt.encode(payload, os.getenv("JWT_SECRET_KEY")).decode()
    response = jsonify(authToken=auth_token, userId=userId, expires=exp)
    response.status_code = 200
    return response


def check_required_fields(required_fields, request_json):
    for k in required_fields:
        if k not in request_json:
            response = make_response((f"{k} field is mandatory.", 400))
            return response
