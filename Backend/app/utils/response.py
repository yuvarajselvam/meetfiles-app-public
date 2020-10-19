from flask import jsonify


def check_required_fields(required_fields, request_json):
    for k in required_fields:
        if k not in request_json:
            response = jsonify(message=f"{k} field is mandatory.")
            response.status_code = 400
            return response
