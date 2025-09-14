#!/usr/bin/env python
# main.py

# Main program for application
# Launch login window to read in username and password.  If user has a record
# check password against saved password.  Comment on whether passwords are same
# or not. If user doesn't have a record save the entered password.
#

import sys

from PyQt6.QtWidgets import QApplication

from gui import LoginWindow, UploadWindow
from excel import find_date_row, find_name_column

from openpyxl import load_workbook

userdata: dict[str, str] = dict()  # username, password, roster_type, roster_path

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
    if roster_path:
        print(f"Opening roster: {roster_path}")
        wb = load_workbook(roster_path)
        if not wb.active:
            sys.stderr.write("No Active Worksheet\n")
            sys.exit(1)
        dates_row = find_date_row(wb.active)
        names_col = find_name_column(wb.active)
        if not names_col:
            sys.stderr.write("Cannot find names column\n")
            sys.exit(1)
        possible_names:dict[str, int] = {
                cell.value:cell.row for cell in wb.active[names_col] if cell.data_type == "s"
        }


# Contact CalDAV server with username/password to get a list of shifts for the
# time period of the roster


# Get user to select his/her name in the roster [NameSelectWindow]


# Get a list of shifts in the roster for the user


# Compare and contrast the shifts that were found in current calendar (if there
# are any) against shifts in the roster


# Show a summary of changes (if any) from shifts found in current calendar


# Update the shifts in the CalDAV server
