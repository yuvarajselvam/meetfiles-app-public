import pytz

from datetime import datetime
from dateutil import parser, rrule

weekday_map = {"monday": 0, "tuesday": 1, "wednesday": 2,
               "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
position_map = {"first": 1, "second": 2, "third": 3, "fourth": 4, "last": -1}


def get_datetime(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = pytz.utc.localize(value)
        return value
    if value:
        tz = None
        if isinstance(value, (tuple, list)):
            value, tz = value
        value = parser.parse(value)
        if tz and value.tzinfo is None:
            tz = pytz.timezone(tz)
            value = tz.localize(value)
        if value.tzinfo is None:
            value = pytz.utc.localize(value)
    return value


def get_rrule_from_pattern(rp):
    if not rp:
        return
    p = rp["pattern"]
    r = rp["range"]
    end = None
    count = None
    start = parser.parse(r["startDate"])
    if r["type"] == "numbered":
        count = r["numberOfOccurrences"]
    elif r["type"] == "endDate":
        end = parser.parse(r["endDate"])
    elif r["type"] == "noEnd":
        pass
    else:
        raise ValueError("Invalid range type")

    if p["type"] == "daily":
        rr = rrule.rrule(freq=rrule.DAILY, interval=p["interval"],
                         count=count, until=end, dtstart=start)
    elif p["type"] == "weekly":
        wkst = weekday_map[p.get("firstDayOfWeek", "sunday").lower()]
        weekdays = [weekday_map[wd.lower()] for wd in p["daysOfWeek"]]
        rr = rrule.rrule(freq=rrule.WEEKLY, interval=p["interval"], wkst=wkst, byweekday=weekdays,
                         count=count, until=end, dtstart=start)

    elif p["type"] == "absoluteMonthly":
        rr = rrule.rrule(freq=rrule.MONTHLY, interval=p["interval"], bymonthday=p["dayOfMonth"],
                         count=count, until=end, dtstart=start)
    elif p["type"] == "absoluteYearly":
        rr = rrule.rrule(freq=rrule.YEARLY, interval=p["interval"],
                         bymonthday=p["dayOfMonth"], bymonth=p["month"],
                         count=count, until=end, dtstart=start)

    elif p["type"] == "relativeMonthly":
        setpos = position_map[p.get("index", "first").lower()]
        weekdays = [weekday_map[wd.lower()] for wd in p["daysOfWeek"]]
        rr = rrule.rrule(freq=rrule.MONTHLY, interval=p["interval"], bysetpos=setpos,
                         byweekday=weekdays, count=count, until=end, dtstart=start)
    elif p["type"] == "relativeYearly":
        setpos = position_map[p.get("index", "first").lower()]
        weekdays = [weekday_map[wd.lower()] for wd in p["daysOfWeek"]]
        rr = rrule.rrule(freq=rrule.YEARLY, interval=p["interval"], bysetpos=setpos,
                         byweekday=weekdays, bymonth=p["month"],
                         count=count, until=end, dtstart=start)
    else:
        raise ValueError('Invalid pattern type')
    return [rule for rule in str(rr).split('\n') if not rule.startswith('DTSTART')]


def get_start_times(recurrence, start):
    recurrence = list(map(lambda x:
                          x.replace('VALUE=DATE:', 'VALUE=DATE-TIME:')
                          if x.startswith('RDATE') else x, recurrence))
    start = get_datetime(start).astimezone(pytz.utc).replace(tzinfo=None)
    return list(rrule.rrulestr('\n'.join(recurrence), dtstart=start))
