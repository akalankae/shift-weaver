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


# Contact CalDAV server with username/password to get a list of shifts for the
# time period of the roster


# Get user to select his/her name in the roster [NameSelectWindow]


# Get a list of shifts in the roster for the user


# Compare and contrast the shifts that were found in current calendar (if there
# are any) against shifts in the roster


# Show a summary of changes (if any) from shifts found in current calendar


# Update the shifts in the CalDAV server
