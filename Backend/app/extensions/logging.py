import logging


class Logger:
    app = None

    def __init__(self, app=None):
        if app:
            self.init_app(app)

    def init_app(self, app):
        logging.addLevelName(12, "REQUEST")
        logging.addLevelName(11, "RESPONSE")
        # noinspection PyArgumentList
        logging.basicConfig(format='[{levelname:>8s}] - {name} - {message}', style='{', level=logging.ERROR)
        app.logger.setLevel(logging.ERROR)
        self.app = app

    @staticmethod
    def log_request(self, request):
        try:
            s = f"{(str(request.path) + ' ' + str(request.method)).ljust(80, ' ')}\n\n"

            if request.method in ['POST', 'PUT']:
                req = request.get_json()
            else:
                req = request.args

            for k, v in req.items():
                if isinstance(v, str):
                    s += f"{k:<14s} : {v:<181.181s}\n"
                elif isinstance(v, list):
                    s += f"{k:<14s} : {str(len(v)) + ' item(s) received.':<81.81s}\n"
            self.log(12, s)
        except Exception as e:
            print(str(e))

    @staticmethod
    def log_response(self, response):
        try:
            if response:
                s = f"{str(response.status_code).ljust(80, ' ')}\n\n"
                if response.json:
                    for k, v in response.json.items():
                        if isinstance(v, str):
                            s += f"{k:<14s} : {v:<181.181s}\n"
                        elif isinstance(v, list):
                            s += f"{k:<14s} : {str(len(v)) + ' item(s) returned.':<181.181s}\n"
                else:
                    s = response.data
                if isinstance(s, str):
                    s += "\n"
                    s += "".center(200, '-')
                    s += '\n'
                    self.log(11, s)
        except Exception as e:
            print(str(e))

