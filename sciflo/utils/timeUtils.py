# -----------------------------------------------------------------------------
# Name:        time.py
# Purpose:     Various time utilities.
#
# Author:      Gerald Manipon
#
# Created:     Tue May 17 08:16:11 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# -----------------------------------------------------------------------------
import time
import types
import string
import re
import datetime
import calendar

_weekdayName = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

_monthName = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def getTimeElementsFromString(dtStr):
    """Return tuple of (year,month,day,hour,minute,second) from date time string."""

    match = re.match(
        r'^(\d{4})[/-](\d{2})[/-](\d{2})[\s*T](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?Z?$', dtStr)
    if match:
        (year, month, day, hour, minute, second) = list(map(int, match.groups()))
    else:
        match = re.match(r'^(\d{4})[/-](\d{2})[/-](\d{2})$', dtStr)
        if match:
            (year, month, day) = list(map(int, match.groups()))
            (hour, minute, second) = (0, 0, 0)
        else:
            raise RuntimeError("Failed to recognize date format: %s" % dtStr)
    return (year, month, day, hour, minute, second)


def getDatetimeFromString(dtStr):
    """Return datetime object from date time string."""

    (year, month, day, hour, minute, second) = getTimeElementsFromString(dtStr)
    return datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute,
                             second=second)


def getEpochFromTimeString(timeStr):
    """Return epoch from a time string: '%Y-%m-%d %H:%M:%S'."""

    #timeTuple = time.strptime(string.split(timeStr,'.')[0],'%Y-%m-%d %H:%M:%S')
    # epoch=time.mktime(timeTuple)-time.timezone
    return float(calendar.timegm(getTimeElementsFromString(timeStr)))


def getDateTimeString():
    """Return the current date and time formatted for a message header."""

    now = time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(now)
    s = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (_weekdayName[wd], day, _monthName[month],
                                                 year, hh, mm, ss)
    return s


def getDateTimeLogString():
    """Return the current time formatted for logging."""

    now = time.time()
    year, month, day, hh, mm, ss, x, y, z = time.localtime(now)
    s = "%02d/%3s/%04d %02d:%02d:%02d" % (day,
                                          _monthName[month], year, hh, mm, ss)
    return s


def getISODateTimeString(fraction=False):
    """Return the current date and time formatted for a message header."""

    now = time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(now)
    if fraction:
        frac = now - int(now)
        s = "%04d-%02d-%02dT%02d:%02d:%02d%sZ" % (
            year, month, day, hh, mm, ss, str(frac)[1:])
    else:
        s = "%04d-%02d-%02dT%02d:%02d:%02dZ" % (year, month, day, hh, mm, ss)
    return s
