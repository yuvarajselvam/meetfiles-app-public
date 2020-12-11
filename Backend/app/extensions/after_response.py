import logging
import traceback
from werkzeug.wsgi import ClosingIterator


logger = logging.getLogger(__name__)


class AfterResponse:
    def __init__(self, app=None):
        self.callbacks = []
        if app:
            self.init_app(app)

    def __call__(self, callback):
        self.callbacks.append(callback)
        return callback

    def init_app(self, app):
        # install extension
        app.after_response = self

        # install middleware
        app.wsgi_app = AfterResponseMiddleware(app.wsgi_app, self)

    def flush(self):
        while self.callbacks:
            try:
                self.callbacks.pop()()
            except Exception:
                logger.error("\n\n--- Traceback Begins ".ljust(184, '-') + "\n\n" +
                             traceback.format_exc() +
                             "\n--- Traceback Ends ".ljust(184, '-') + "\n\n")


class AfterResponseMiddleware:
    def __init__(self, application, after_response_ext):
        self.application = application
        self.after_response_ext = after_response_ext

    def __call__(self, environ, after_response):
        iterator = self.application(environ, after_response)
        try:
            return ClosingIterator(iterator, [self.after_response_ext.flush])
        except Exception:
            traceback.print_exc()
            return iterator
