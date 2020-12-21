import logging


class Logger:
    app = None

    def __init__(self, app=None):
        self.logger = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        logging.addLevelName(42, "REQUEST")
        logging.addLevelName(41, "RESPONSE")
        # noinspection PyArgumentList
        logging.basicConfig(format='[{levelname:>8s}] {asctime}s - {name} - {message}',
                            style='{', level=logging.WARN)
        self.logger = logging.getLogger('server')
        app.logger.setLevel(logging.ERROR)
        logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        self.app = app

    def log(self, request, response, status_code=None):
        try:
            s = str(request.method) + ' ' + str(request.path)
            if status_code:
                s += (' ' + str(status_code))
            s = s.ljust(80, ' ') + "\n"

            if request.method in ['POST', 'PUT']:
                req = request.get_json()
            else:
                req = request.args

            if response:
                s += "\n"
                for k, v in req.items():
                    if isinstance(v, str):
                        s += f"{k:<18s} : {v:<181.181s}\n"
                    elif isinstance(v, list):
                        s += f"{k:<18s} : {str(len(v)) + ' item(s) received.':<81.81s}\n"
            if not response:
                s += ('\n' + "".center(180, '-') + '\n')
            self.logger.log(42, s)

            if response:
                s = f"{str(response.status_code).ljust(80, ' ')}\n\n"
                if response.json:
                    if isinstance(response.json, dict):
                        for k, v in response.json.items():
                            if isinstance(v, str):
                                s += f"{k:<18s} : {v:<181.181s}\n"
                            elif isinstance(v, list):
                                s += f"{k:<18s} : {str(len(v)) + ' item(s) returned.':<181.181s}\n"
                    elif isinstance(response.json, list):
                        s += f"{str(len(response.json)) + ' item(s) returned.':<181.181s}\n"
                else:
                    s += str(response.data)
                s += "\n"
                s += "".center(180, '-')
                s += '\n\n'
                self.logger.log(41, s)
        except Exception as e:
            print(str(e))

