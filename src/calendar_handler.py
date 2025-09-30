#!/usr/bin/env python
# caltest.py
# Testing communication with icloud CalDAV server and updating calendar data.

import sys
from datetime import date

from caldav.collection import Calendar
from caldav.davclient import get_davclient
from caldav.lib.error import AuthorizationError, NotFoundError
from icalendar.cal import Event


def get_existing_calendar(
    credentials: dict[str, str],
    calendar_name: str,
) -> Calendar | None:
    """
    Try and get a calendar instance from icloud CalDAV server.
    If username/password is wrong, raises AuthroizationError.
    If requested calendar was not found, raises NotFoundError.
    For any other type of exception, its simply printed out and re-raised.
    """
    ICLOUD_URL = "https://caldav.icloud.com/"
    config_data = {
        "url": ICLOUD_URL,
        "username": credentials["username"],
        "password": credentials["password"],
    }
    with get_davclient(**config_data) as client:
        try:
            principal = client.principal()
            calendar = principal.calendar(calendar_name)
        except AuthorizationError as err:
            sys.stderr.write(f"Wrong username/password: {err}\n")
            raise err
        except NotFoundError as err:
            sys.stderr.write(f"{calendar_name} was not found: {err}\n")
            raise err
        except Exception as err:
            sys.stderr.write(f"{err}\n")
            raise err
        else:
            return calendar


# Extract current calendar data
# Input:
# - user credentials for icloud server - username & password
# - name of the calendar to look up - if missing let user know and create one
# - starting and ending dates for the period
def get_shifts_from_calendar(calendar: Calendar, from_: date, to: date) -> list[Event]:
    shifts: list[Event] = list()
    for event in calendar.search(start=from_, end=to, expand=True, event=True):
        shifts.append(event.component)
    return shifts


# Get the list of (names of) existing calendars from icloud
# If credentials are incorrect raise `AuthorizationError`
def get_calendar_list(username: str, password: str, url: str|None = None) -> list[str]:
    calendar_list: list[str] = []
    if url is None:
        url = r"https://caldav.icloud.com/"
    with get_davclient(url=url, username=username, password=password) as client:
        try:
            principal = client.principal()
        except AuthorizationError as err:
            sys.stderr.write(f"Username/password is incorrect: {err}\n")
            raise err
        else:
            for cal in principal.calendars():
                if cal and cal.name:
                    calendar_list.append(cal.name)
    return calendar_list

if __name__ == '__main__':
    username = "akalankae84@icloud.com"
    password = "siqm-wprd-skeg-rqlx"
    try:
        existing_calendars = get_calendar_list(username, password)
    except AuthorizationError:
        print("Could not access iCloud server")
    else:
        print(f"Found {len(existing_calendars)} calendars")
        for i, calendar in enumerate(existing_calendars, 1):
            print(f"{i} {calendar}")
