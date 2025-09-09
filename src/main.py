#!/usr/bin/env python
# main.py
# Main program for application

import hashlib
import json
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from gui import LoginWindow  # , UploadWindow, NameSelectWindow

SECRETS_DIR = "data"  # directory where user credential files are saved


userdata: dict[str, str] = dict()

app = QApplication(sys.argv)

win = LoginWindow(userdata)
win.show()

app.exec()

# NOTE: You have to make sure username/password are not empty strings
print(f"Username: {userdata.get('username')}")
print(f"Password: {userdata.get('password')}")

username = userdata.get("username", "")
username_hexdigest = hashlib.md5(username.encode()).hexdigest()
secrets_dir = Path(SECRETS_DIR)
secrets_path = secrets_dir.joinpath(username_hexdigest)
if secrets_path.is_file():
    try:
        with secrets_path.open("r") as f:
            saved_userdata = json.load(f)
    except OSError as err:
        sys.stderr.write(f"{err}\n")
        sys.stderr.write(f"Cannot create {secrets_path} while {SECRETS_DIR} exists\n")
        sys.exit(1)
    else:
        saved_password = saved_userdata.get("password")
        username = userdata.get("username")
        password = userdata.get("password")
        if not saved_password:
            sys.stderr.write("user credentials file was found with empty password!\n")
            sys.exit(2)
        if saved_password != password:
            sys.stderr.write(f"Saved password for {username} doesn't match just now!\n")
            sys.exit(3)
        print(f"Saved password for {username} matches existing password")


if not secrets_dir.is_dir():
    try:
        secrets_dir.mkdir()
    except FileExistsError as err:
        sys.stderr.write(f"{err}\n")
        sys.exit(1)
    else:
        with secrets_path.open("w") as secrets_file:
            json.dump(userdata, secrets_file)
