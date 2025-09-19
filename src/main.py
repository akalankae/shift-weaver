#!/usr/bin/env python
# main.py

# Main program for application
# Launch login window to read in username and password.  If user has a record
# check password against saved password.  Comment on whether passwords are same
# or not. If user doesn't have a record save the entered password.
#

import sys
from datetime import date, datetime
import pickle

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

    print(f"User's name in roster: {name_in_roster}")
    if name_in_roster:
        print(f"User's row in roster: {names.get(name_in_roster)}")
    else:
        print("User's name was not found in roster")

    shift_values = [cell.value for cell in worksheet[user_row][start_col:]]

    # Report back about number of working days and number of shift
    print(f"Found {len(dates)} dates.")
    print(f"Found {len(shift_values)} shifts.")

    shifts: dict[date, str] = {}  # Dict of shifts for the term: date -> shift
    for dt, shift_symbol in zip(dates, shift_values):
        if isinstance(dt, datetime) and (
            shift_symbol
            and isinstance(shift_symbol, str)
            and (shift_symbol := shift_symbol.strip())
            and shift_symbol.upper() not in ("OFF")
        ):
            shifts[dt.date()] = shift_symbol

    shift_labels: set[str] = set()
    shift_dates: set[date] = set()
    for shift_date, shift_symbol in shifts.items():
        shift_dates.add(shift_date)
        shift_labels.add(shift_symbol)

    # Show the shifts: dates and symbols
    print("Following shift symbols were found:")
    for label in shift_labels:
        print(f"* {label}")

    print("\nYou have work on following dates:")
    for i, shift_date in enumerate(sorted(shift_dates), 1):
        print(f"{i:>3d} {shift_date}")

    # Try to make sense of the shift symbols by looking them up in our records
    new_labels: dict[str, str] = {}
    try:
        with open("data/shifts.dat", "rb") as f:
            known_shift_labels.update(pickle.load(f))
    except IOError as err:
        sys.stderr.write("Cannot find previously saved shift symbols for analysis!\n")
        sys.stderr.write(f"{err}\n")
    else:
        for label in shift_labels:
            meaning = known_shift_labels.get(label)
            # If the label is not in the records, prompt the user on how it
            # should be interpreted and then save this for future use.
            if not meaning:
                print(f'"{label}" is unknown!')
                meaning = input(f'Enter a label for "{label}"\n\t>> ').rstrip()
                new_labels[label] = meaning
            else:
                print(f"{label}: {meaning}")
        if new_labels:
            known_shift_labels.update(new_labels)
            with open("data/shifts.dat", "wb") as f:
                try:
                    pickle.dump(known_shift_labels, f)
                except IOError as err:
                    sys.stderr.write(f"Could not save newly added labels.\n{err}\n")

        print("\n{}   {}".format("Date of Shift".center(15), "Shift".center(15)))
        for shift_date, shift_label in shifts.items():
            date_str = shift_date.strftime("%d %b %Y")
            print(f"{date_str:>15s} | {known_shift_labels.get(shift_label):<12s}")



# Compare and contrast the shifts that were found in current calendar (if there
# are any) against shifts in the roster


# Show a summary of changes (if any) from shifts found in current calendar


# Update the shifts in the CalDAV server
