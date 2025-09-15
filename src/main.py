#!/usr/bin/env python
# main.py

# Main program for application
# Launch login window to read in username and password.  If user has a record
# check password against saved password.  Comment on whether passwords are same
# or not. If user doesn't have a record save the entered password.
#

import sys
from datetime import datetime

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string
from PyQt6.QtWidgets import QApplication

from excel import filter_names_dict, find_date_row, find_name_column
from gui import LoginWindow, NameSelectWindow, UploadWindow

userdata: dict[str, str] = dict(
    username="",  # icloud login name (email)
    password="",  # icloud calendar server password
    roster_type="",  # type of roster: term / week
    roster_path="",  # path to roster excel file
    name_in_roster="",  # name of the user in the roster
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

    print(f"User's name in roster: {name_in_roster}")
    if name_in_roster:
        print(f"User's row in roster: {names.get(name_in_roster)}")
    else:
        print("User's name was not found in roster")

    shift_values = [cell.value for cell in worksheet[user_row][start_col:]]
    print(f"Found {len(dates)} dates.")
    print(f"Found {len(shift_values)} shifts.")

    for dt, shift_symbol in zip(dates, shift_values):
        if isinstance(dt, datetime) and (
            shift_symbol
            and isinstance(shift_symbol, str)
            and (shift_symbol := shift_symbol.strip())
            and shift_symbol.upper() not in ("OFF")
        ):
            print(f"{dt.date()} {shift_symbol}")


# Get a list of shifts in the roster for the user


# Compare and contrast the shifts that were found in current calendar (if there
# are any) against shifts in the roster


# Show a summary of changes (if any) from shifts found in current calendar


# Update the shifts in the CalDAV server
