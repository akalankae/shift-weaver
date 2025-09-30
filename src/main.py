#!/usr/bin/env python
# main.py

# Main program for application
# Launch login window to read in username and password.  If user has a record
# check password against saved password.  Comment on whether passwords are same
# or not. If user doesn't have a record save the entered password.
#

import sys
from datetime import datetime

from caldav.davclient import get_davclient
from caldav.lib.error import AuthorizationError, NotFoundError, PutError
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string
from PyQt6.QtWidgets import QApplication

from term_roster_parser import filter_names_dict, find_date_row, find_name_column
from gui import LoginWindow, NameSelectWindow, UploadWindow
from shift import Shift
from calendar_handler import get_shifts_from_calendar


# Debug to error file
from pathlib import Path

ERROR_FILE = "data/errors.log"


userdata: dict[str, str] = dict(
    username="",  # icloud login name (email)
    password="",  # icloud calendar server password
    roster_type="",  # type of roster: term / week
    roster_path="",  # path to roster excel file
    name_in_roster="",  # name of the user in the roster
)

known_shift_labels: dict[str, str] = dict(
    D="Day",
    MF="Morning Float",
    F="Float",
    E="Evening",
    N="Night",
    ADO="Allocated Day-Off",
    T="Teaching Day",
    SR="Sick Relief",
)

# Get user credentials [LoginWindow]
app = QApplication(sys.argv)
login_win = LoginWindow(userdata)
login_win.show()

app.exec()

# Upload user excel file [UploadWindow]
upload_win = UploadWindow(userdata)
upload_win.show()

app.exec()

# Get a list of names in the roster
roster_type = userdata.get("roster_type")
if roster_type == "term":
    roster_path = userdata.get("roster_path")
    if not roster_path:
        sys.stderr.write(f"Could nof find roster: {roster_path}")
        sys.exit(1)
    print(f"Opening roster: {roster_path}")
    wb = load_workbook(roster_path, data_only=True)
    worksheet = wb.active
    if not worksheet:
        sys.stderr.write("No Active Worksheet\n")
        sys.exit(1)
    try:
        dates_row: int = find_date_row(worksheet)
    except AssertionError as err:
        sys.stderr.write(f"{err}\n")
        sys.exit(2)
    names_col: str = find_name_column(worksheet)
    if not names_col:
        sys.stderr.write("Cannot find names column\n")
        sys.exit(1)
    possible_names: dict[str, int] = {
        cell.value: cell.row for cell in worksheet[names_col] if cell.data_type == "s"
    }
    names = filter_names_dict(possible_names)

else:
    print(f"Roster type: {userdata.get('roster_type')}")
    sys.exit(0)


# Contact CalDAV server with username/password to get a list of shifts for the
# time period of the roster


# Get user to select his/her name in the roster [NameSelectWindow]
if roster_type == "term":
    name_select_win = NameSelectWindow(list(sorted(names.keys())), userdata)
    name_select_win.show()

    app.exec()

    print(f"Roster: {roster_path}")
    print(f"Dates row: {dates_row}")
    print(f"Names col: {names_col}")

    # Dates of term start immediately after the column with names
    start_col = column_index_from_string(names_col)
    dates = [cell.value for cell in worksheet[dates_row][start_col:]]
    name_in_roster = userdata.get("name_in_roster")
    if not name_in_roster:
        sys.stderr.write(f"Name {name_in_roster} was not found.\n")
        sys.exit(1)
    user_row = names.get(name_in_roster)
    if not user_row:
        sys.stderr.write(f"User row: {user_row} for {name_in_roster} is invalid\n")
        sys.exit(1)

    print(f"User {name_in_roster} is at row number {user_row}")  # Dbg

    # Get the slice of the user's row containing the dates
    shift_values = [cell.value for cell in worksheet[user_row][start_col:]]

    # Make sure number of shifts is equal to number of dates with shifts.
    print(f"Dates: {len(dates)} | Shifts: {len(shift_values)}")  # Dbg
    assert len(dates) == len(shift_values)  # Dbg

    # Get first and last dates of the term. This is required to search for what
    # already exists in the CalDAV server.
    filtered_dates: list[datetime] = list(filter(None, dates))
    min_date = min(filtered_dates)
    max_date = max(filtered_dates)
    print(f"Term from: {min_date.date()} to {max_date.date()}")

    # Zip dates (datetime objects) and labels in roster to make a dict and
    # create icalendar Events (`Shift`) from data for each shift then add them
    # to a list
    shifts: list[Shift] = []  # List of shifts for the term
    for dt, shift_label in zip(dates, shift_values):
        if isinstance(dt, datetime) and (
            shift_label  # not None
            and isinstance(shift_label, str)  # a string
            and (shift_label := shift_label.strip())  # not empty/whitespace only
            and shift_label.upper() not in ("OFF")  # `OFF` days are just empty
        ):
            shifts.append(Shift(dt.date(), shift_label))

    # # -------------------- NEED TO FIX BEYOND THIS POINT! ---------------------
    # # Try to make sense of the shift symbols by looking them up in our records
    # new_labels: dict[str, str] = {}
    # try:
    #     with open("data/shifts.dat", "rb") as f:
    #         known_shift_labels.update(pickle.load(f))
    # except IOError as err:
    #     sys.stderr.write("Cannot find previously saved shift symbols for analysis!\n")
    #     sys.stderr.write(f"{err}\n")
    # else:
    #     for label in shift_labels:
    #         meaning = known_shift_labels.get(label)
    #         # If the label is not in the records, prompt the user on how it
    #         # should be interpreted and then save this for future use.
    #         if not meaning:
    #             print(f'"{label}" is unknown!')
    #             meaning = input(f'Enter a label for "{label}"\n\t>> ').rstrip()
    #             new_labels[label] = meaning
    #         else:
    #             print(f"{label}: {meaning}")
    #     if new_labels:
    #         known_shift_labels.update(new_labels)
    #         with open("data/shifts.dat", "wb") as f:
    #             try:
    #                 pickle.dump(known_shift_labels, f)
    #             except IOError as err:
    #                 sys.stderr.write(f"Could not save newly added labels.\n{err}\n")
    #
    #     print("\n{}   {}".format("Date of Shift".center(15), "Shift".center(15)))
    #     for shift_date, shift_label in shifts.items():
    #         date_str = shift_date.strftime("%d %b %Y")
    #         print(f"{date_str:>15s} | {known_shift_labels.get(shift_label):<12s}")

    # # -------------------- NEED TO FIX UPTO THIS POINT! ---------------------

    # # Create a new calendar for testing and add shift (events) to it and write
    # # back to a local file
    # my_calendar = Calendar()
    # my_calendar.calendar_name = "Roster"
    # my_calendar.uid = str(uuid4())
    # my_calendar.categories = ["Work", "Shift"]
    # for shift in shifts:
    #     my_calendar.add_component(shift)
    # with Path("data/my_calendar.ics").open("wb") as f:
    #     f.write(my_calendar.to_ical())


# Compare and contrast the shifts that were found in current calendar (if there
# are any) against shifts in the roster
if roster_type == "term":
    error_file = Path(ERROR_FILE).open("a+b")
    # Get shifts for the term
    CALENDAR_NAME = "Test Calendar"
    try:
        URL = "https://caldav.icloud.com/"
        # Dbg - PutError at '404 not found
        print(
            f"Username: {userdata['username']} | Password: {userdata['password']} | URL: {URL}"
        )
        with get_davclient(
            url=URL,
            username=userdata["username"],
            password=userdata["password"],
        ) as davclient:
            principal = davclient.principal()
            try:
                target_cal = principal.calendar(name=CALENDAR_NAME)
            except NotFoundError:
                print(f"Could not find calendar: {CALENDAR_NAME}")
                target_cal = principal.make_calendar(name=CALENDAR_NAME)
                print(f"Created new calendar: {CALENDAR_NAME}")
            else:
                print(f"Created new calendar: {CALENDAR_NAME}")
    except AuthorizationError as err:
        sys.stderr.write(f"Issue with authorization: {CALENDAR_NAME}\n{err}\n")
        sys.exit(1)
    else:
        if target_cal is not None:
            existing_shifts = get_shifts_from_calendar(
                target_cal, min_date.date(), max_date.date()
            )
            print(f"Found {len(existing_shifts)} shifts")
            if len(existing_shifts) == 0:
                print(f"Inserting {len(shifts)} shifts to calendar: {CALENDAR_NAME}")
                for shift in shifts:
                    try:
                        ical_data = shift.to_ical()
                        target_cal.save_event(ical=ical_data)
                    except Exception as err:
                        print(f"ical_data (type): {type(ical_data)}")
                        error_file.write(f"{err}\n\n")
                        error_file.write(f"{ical_data}\n")
            else:
                new_shifts: list[Shift] = []
                for shift in shifts:
                    #     if shift not in found_shifts:
                    #         new_shifts.append(shift)
                    # Below code is commented because `in` seem to work
                    # (checkout Shift.__eq__() method)
                    for existing_shift in existing_shifts:
                        if shift == existing_shift:
                            break
                    else:
                        new_shifts.append(shift)
                for i, shift in enumerate(new_shifts, 1):
                    # error_file = Path(ERROR_FILE).open("wb")
                    try:
                        ical_data = shift.to_ical()
                        _code = target_cal.save_event(
                            ical=ical_data, no_overwrite=False, no_create=False
                        )
                    except PutError as err:
                        sys.stderr.write(
                            f"Failed to insert {shift.get('summary')}-{shift.uid} to calendar\n"
                        )
                        sys.stderr.write(f"{err}\n")
                        sys.stderr.write(ical_data.decode("utf8"))
                        sys.stderr.write("\n")
                    else:
                        print(f"Return Code: {_code}")
    #                     finally:
    #                         print(f"""
    #         # New Shift #{i}
    #         APPLICATION: {shift.get("x-published-by", "<Not Found>")}
    #         Shift Summary: {shift.get("summary", "<Not Found>")}\tShift UID: {shift.uid}
    #         From: {shift.start}\tTo  : {shift.end}
    #         =====================================================================================
    # """)
    # error_file.close()
    error_file.close()


# Show a summary of changes (if any) from shifts found in current calendar


# Update the shifts in the CalDAV server
