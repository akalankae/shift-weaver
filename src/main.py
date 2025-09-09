#!/usr/bin/env python
# main.py
# Main program for application

import sys

from PyQt6.QtWidgets import QApplication

from gui import LoginWindow  #, UploadWindow, NameSelectWindow


userdata: dict[str, str] = dict()

app = QApplication(sys.argv)

win = LoginWindow(userdata)
win.show()

app.exec()

print(f"Username: {userdata.get('username')}")
print(f"Password: {userdata.get('password')}")
