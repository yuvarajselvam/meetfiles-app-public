import pytz
from datetime import datetime


def get_datetime(value):
    if value:
        tz = None
        if isinstance(value, (tuple, list)):
            value, tz = value

        if '.' in value:
            value = value.split('.')
            value[1] = value[1][:6]
            value = '.'.join(value)

        try:
            value = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f%z' if '.' in value else '%Y-%m-%dT%H:%M:%S%z')
        except ValueError:
            try:
                value = datetime.strptime(value, '%Y-%m-%d')
            except ValueError:
                value = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f' if '.' in value else '%Y-%m-%dT%H:%M:%S')
        if tz:
            value = value.replace(tzinfo=pytz.timezone(tz))
    return value
