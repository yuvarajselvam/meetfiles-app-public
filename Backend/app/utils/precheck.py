from functools import wraps
from flask import request


def precheck(required_fields: list):
    def wrap(f):
        @wraps(f)
        def wrapped_f(*args, **kwargs):
            if request.method in ['POST', 'PUT']:
                request_json = request.get_json()
            elif request.method == 'GET':
                request_json = request.args
            else:
                return f(*args, **kwargs)

            for k in required_fields:
                if not request_json or k not in request_json:
                    return {"Error": f"`{k}` field is mandatory."}, 400

            return f(*args, **kwargs)
        return wrapped_f
    return wrap
