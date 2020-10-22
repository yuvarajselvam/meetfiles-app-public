from flask import request


def precheck(required_fields=None, subdomain=True):
    def wrap(f):
        def wrapped_f(*args, **kwargs):
            if request.method in ['POST', 'PUT']:
                request_json = request.get_json()
            elif request.method == 'GET':
                request_json = request.args
            else:
                return f(*args, **kwargs)

            if required_fields:
                for k in required_fields:
                    if k not in request_json:
                        return {"Error": f"{k} field is mandatory."}, 400

            if subdomain:
                sub_domain = request.subdomain.strip()
                if not sub_domain or str(sub_domain) == 'app':
                    return {"Error": f"Invalid subdomain for this request:{sub_domain}"}, 400
            return f(*args, **kwargs)
        return wrapped_f
    return wrap
