#!/usr/bin/env python
# Handle shifts in the term roster

import uuid
from datetime import date, datetime, time, timedelta
from typing import final, override, Self
from zoneinfo import ZoneInfo

from icalendar import Event

APP_VERSION = "0.1"
APP_NAME = "ShiftWeaver"
_MY_TIMEZONE = ZoneInfo("Australia/Sydney")
_APP_NAMESPACE = uuid.UUID("48f80ff6-3ddd-4b70-9ad0-24459b3219bc")
_EMPLOYEE_ID = "60316064"  # My SWSLHD ID
_EMPLOYER_NAME = "SWSLHD"  # Local Health District


@final
class Shift(Event):
    """
    NOTE: Time zone is hard coded as Australia/Sydney
    """
    APP_NAME = APP_NAME
    APP_VERSION = APP_VERSION

    # Use a decorator to read a file update this dict so the user can modify
    # what the labels mean if required.
    LABEL_MEANING = dict(
        D="Day",  # datetime
        MF="Morning Float",  # datetime
        F="Float",  # datetime
        E="Evening",  # datetime
        N="Night",  # datetime
        SR="Sick Relief",  # date
        T="Teaching Day",  # date
        AL="Annual Leave",  # date
    )
    SHIFT_START_TIMES = dict(
        D=time(8, 0, 0, tzinfo=_MY_TIMEZONE),  # 8.00 AM
        MF=time(10, 0, 0, tzinfo=_MY_TIMEZONE),  # 10.00 AM
        F=time(12, 30, 0, tzinfo=_MY_TIMEZONE),  # 12.30 PM
        E=time(14, 0, 0, tzinfo=_MY_TIMEZONE),  # 2.00 PM
        N=time(22, 30, 0, tzinfo=_MY_TIMEZONE),  # 10.30 PM
    )

    def __init__(self, shift_date: date, shift_label: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        shift_label = shift_label.strip().upper()  # ? methods maybe unnecessary
        self.date = shift_date  # offset-naive (self.start/self.end are not)

        # Shifts have a start time, others do not. So DTSTART property of shifts
        # are parameters with DATE-TIME values. But all non-shifts' DTSTART
        # property have DATE parameter values.
        if shift_label in __class__.SHIFT_START_TIMES:
            start_time = __class__.SHIFT_START_TIMES[shift_label]
            shift_start = datetime.combine(shift_date, start_time)
            self.add("DTSTART", shift_start)
            self.add("DURATION", timedelta(hours=10))
        else:
            # Looks like icloud's caldav server doesn't support DATE object. I
            # have to use DATE-TIME objects instead. If it did DTSTART, DTEND
            # properties would have been written as DTSTART;VALUE=DATE:20250810
            # for example. And duration would have been 1 day
            # This seem to raise PutError '404 not found
            # self.add("dtstart", shift_date)  # Whole day event with no time-of-day
            self.add("DTSTART", datetime.combine(shift_date, time(0, 0, 0)))
            self.add("DURATION", timedelta(hours=24))

        shift_summary = __class__.LABEL_MEANING.get(shift_label, shift_label)
        self.add("SUMMARY", shift_summary)
        self.uuid = self.__generate_uid()  # combination of emp ID, employer & shift
        self.uid = str(self.uuid)
        self.categories = ["Work", "Shift"]
        self.add("CLASS", "PRIVATE")
        self.sequence = 0  # increment this each time the shift is modified
        self.add("X-PUBLISHED-BY", f"{self.APP_NAME}")  # use this to filter out shifts


    # DATE-TIME of DTSTART property determines the sorting order.
    def __lt__(self, other:Self)->bool:
        """
        datetime value of DTSTART property of the VEVENT dictates the sorting order.
        """
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.start < other.start

    # Integral value of UUID of the VEVENT determines hash value and uniqueness
    @override
    def __hash__(self)->int:
        """
        Integral value of UUID of the VEVENT determines hash value and uniqueness.
        """
        return self.uuid.int

    def __generate_uid(self)->uuid.UUID:
        """
        Generate deterministic UID compliant with RFC 4122 section 4.4 and 4.5
        UID is generated using hash of random hardcoded string AND SHA1 hash of
        a string generated using starting date-time (or date) of a shift. Format
        of this generated string is:
            EMPLOYER_NAME:EMPLOYEE_ID:SHIFT_START_DATETIME
        Note datetime used here is agnostic of time zone, but because what the
        timezone is depends on the datetime it should not matter.
        i.e. For Sydney from April to October it would be AEST (or +1000) and
        from October to April it would be AEDT (or +1100). Same datetime gets
        same timezone component so it doesn't affect UID.
        """
        shift_string = self.start.strftime("%Y%m%d%H%M%S%Z")
        deterministic_string = f"{_EMPLOYER_NAME}:{_EMPLOYEE_ID}:{shift_string}"
        uid = uuid.uuid5(_APP_NAMESPACE, deterministic_string)
        return uid

    @override
    def __eq__(self, other: object) -> bool:
        # def __eq__(self, other: typing.Self)->bool:
        """
        This is used by `==` operation as well as `in` operation.
        Enforce `other` is of same class as `self`
        """
        if not isinstance(other, type(self)):
            return NotImplemented

        return self.uid == other.uid


if __name__ == "__main__":
    shift = Shift(date.today(), "D")
    print(shift)
