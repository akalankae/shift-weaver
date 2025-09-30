#!/usr/bin/env python
# ui.py
# Graphical user interface for the program

import sys
import pickle
from typing import final
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QButtonGroup,
    QHBoxLayout,
    QStackedWidget,
    QPushButton,
    QComboBox,
    QLabel,
    QLineEdit,
    QCheckBox,
    QFormLayout,
    QMessageBox,
    QGroupBox,
    QFrame,
)
from caldav.lib.error import AuthorizationError
from calendar_handler import get_calendar_list


@final
class MainWindow(QMainWindow):
    """
    GUI for the Shift-Weaver application.
    """

    VERSION = "0.1"
    USER_DATA_DIR = "./data"  # directory where user credentials are saved

    def __init__(self):
        super().__init__()
        self.setMinimumSize(QSize(400, 200))
        self.setWindowTitle(f"Shift Weaver v{__class__.VERSION}")
        self.user_data = None

        self.login_window = LoginWindow(self.USER_DATA_DIR)
        self.login_window.login_success.connect(self.handle_login)

        self.calendar_picker_window = None

        self.roster_uploader_window = None

        self.name_selector_window = None

        self.root = QStackedWidget()
        self.root.addWidget(self.login_window)

        self.setCentralWidget(self.root)

    def handle_login(self, data: dict[str, str]):
        self.user_data = data
        calendars: list[str] = []
        # Do whatever is necessary to get the list of calendars from caldav
        # server.
        try:
            calendars.extend(
                get_calendar_list(username=data["username"], password=data["password"])
            )
        except AuthorizationError:
            # Need to stop moving forward to next step
            QMessageBox.critical(
                self,
                "Invalid Credentials",
                "Username and/or password for iCloud was wrong.",
                QMessageBox.StandardButton.Ok,
            )
        else:
            self.calendar_picker_window = CalendarPickerWindow(calendars)

            self.root.addWidget(self.calendar_picker_window)
            self.root.setCurrentWidget(self.calendar_picker_window)


@final
class LoginWindow(QGroupBox):
    """
    Window to read-in user credentials and information.

    Parameters:
      - Optional: user_dir (string)
          Directory into which user credentials are saved.
    """

    login_success = pyqtSignal(dict)

    def __init__(self, user_dir: str | None = None, *args, **kwargs):
        super().__init__("iCloud Credentials")
        self.user_data: dict[str, str] = dict()
        self.user_dir: str | None = user_dir
        self.loaded_from_file: bool = False  # if credentials were read from file

        self.form = QFormLayout()
        self.setLayout(self.form)

        self.username_entry = QLineEdit()
        self.username_entry.setPlaceholderText("john_doe@icloud.com")
        # If user credentials have been saved for this user from a previous run,
        # when leaving username_entry field, read those saved credentials
        self.username_entry.editingFinished.connect(self.read_user_configs)

        self.password_entry = QLineEdit()
        self.password_entry.setPlaceholderText("******")
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.reveal_password_cb = QCheckBox("reveal password")
        self.reveal_password_cb.checkStateChanged.connect(
            self.toggle_password_visibility
        )

        password_layout = QVBoxLayout()
        password_layout.addWidget(self.password_entry)
        password_layout.addWidget(self.reveal_password_cb)

        self.emp_id_entry = QLineEdit()
        self.emp_id_entry.setPlaceholderText("60316064")
        self.employer_entry = QLineEdit()
        self.employer_entry.setPlaceholderText("SWSLHD")

        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.submit)

        self.form.addRow("Username", self.username_entry)
        self.form.addRow("Password", password_layout)
        self.form.addRow("Employee ID", self.emp_id_entry)
        self.form.addRow("Employer", self.employer_entry)
        self.form.addRow(self.submit_button)

    def toggle_password_visibility(self, checkstate):
        "Hide or reveal password"
        if checkstate == Qt.CheckState.Checked:
            self.password_entry.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)

    def read_user_configs(self):
        """
        If we know a user credentials directory and if the user has a file with
        previously saved credentials in it, load password and other fields
        automatically from that file.
        """
        if self.user_dir is None:
            return
        username = self.username_entry.text().strip()
        userdata_file = Path(self.user_dir).joinpath(f"{username}.dat")
        if userdata_file.is_file():
            try:
                with open(userdata_file, "rb") as f:
                    self.user_data = pickle.load(f)
            except IOError as err:
                sys.stderr.write(f"Could not read file: {userdata_file}\n")
                sys.stderr.write(f"{err}\n")
            else:
                self.loaded_from_file = True
                print(f"Userdata loaded from {userdata_file}")

        password = self.user_data.get("password")
        if password:
            self.password_entry.setText(password)
        emp_id = self.user_data.get("id")
        if emp_id:
            self.emp_id_entry.setText(emp_id)
        employer = self.user_data.get("employer")
        if employer:
            self.employer_entry.setText(employer)

    def submit(self):
        # NOTE: You don't need to keep a reference to `user_data`. Once we have
        # got the `Principal` from CalDAV server, we no longer need user
        # credentials. So we can drop the `self` and make `user_data` a local variable.
        self.user_data["username"] = self.username_entry.text().strip()
        self.user_data["password"] = self.password_entry.text().strip()
        self.user_data["id"] = self.emp_id_entry.text().strip()
        self.user_data["employer"] = self.employer_entry.text().strip()
        answer = QMessageBox.information(
            self,
            "User Credentials & Information",
            f"""<p>You Entered Following<p>
            <p>Username: {self.user_data["username"]}<p>
            <p>Password: {self.user_data["password"]}<p>
            <p>Employee ID: {self.user_data["id"]}<p>
            <p>Employer: {self.user_data["employer"]}<p>""",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.No,
        )

        if answer == QMessageBox.StandardButton.Ok:
            print("Login successful")
            self.login_success.emit(self.user_data)  # signal to move on to next
            # If userdata was not loaded from file on the disk (ie. entered by
            # user) and user_dir is given, write to relevant file for the user
            if not self.loaded_from_file and self.user_dir:
                self.update_user_data()
        else:
            self.close()

    def update_user_data(self):
        """
        Write credentials and user information read from user to userdata
        dictionary to the relevant file.
        """
        username = self.user_data["username"]
        userdata_file = f"{self.user_dir}/{username}.dat"
        try:
            with open(userdata_file, "wb") as f:
                pickle.dump(self.user_data, f)
        except IOError as err:
            sys.stderr.write(f"Could not write userdata to {userdata_file}\n")
            sys.stderr.write(f"{err}\n")
        else:
            print(f"Userdata written to {userdata_file}")


@final
class CalendarPickerWindow(QGroupBox):
    """
    Window to pick a calendar to synchronize with roster.
    """

    def __init__(self, calendars: list[str], *args, **kwargs):
        super().__init__("Select a Calendar")

        # Choose one from existing calendars: checkbox + combobox
        self.pick_cal_cb = QCheckBox("Select existing calendar")
        self.pick_cal_cb.setChecked(True)
        self.pick_cal_combo = QComboBox()
        self.pick_cal_combo.addItems(calendars)

        # Create a new calendar: checkbox + lineedit
        self.new_cal_cb = QCheckBox("Create a new calendar")
        self.new_cal_entry = QLineEdit()

        # If list of calendars is empty disable the checkbox + combobox
        if len(calendars) < 1:
            self.pick_cal_cb.setEnabled(False)
            self.pick_cal_combo.setEnabled(False)
        else:
            self.new_cal_cb.setChecked(False)

        # Make above 2 options mutually exclusive
        self.group = QButtonGroup()
        self.group.addButton(self.pick_cal_cb, 0)  # Checkbox #1
        self.group.addButton(self.new_cal_cb, 1)  # Checkbox #2
        self.group.idClicked.connect(self.select_calendar_type)

        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.submit)

        self.form = QFormLayout()
        self.form.addRow(self.pick_cal_cb, self.pick_cal_combo)
        self.form.addRow(self.new_cal_cb, self.new_cal_entry)
        self.form.addRow(self.submit_button)

        self.setLayout(self.form)

    def submit(self):
        # Need to validate if it is a new calendar - May be NOT !!
        pass

    def select_calendar_type(self, i):
        print(f"Clicked ID: {i}")
        if i:
            self.new_cal_entry.setEnabled(True)
            self.pick_cal_combo.setEnabled(False)
        else:
            self.pick_cal_combo.setEnabled(True)
            self.new_cal_entry.setEnabled(False)


@final
class RosterUploaderWindow(QGroupBox):
    """
    Enter a roster file to upload for processing.
    """

    def __init__(self, *args, **kwargs):
        super().__init__("Upload Roster")


@final
class NameSelecterWindow(QGroupBox):
    """
    Display the names in the roster for the user to pick one.
    """

    def __init__(self, *args, **kwargs):
        super().__init__("Select User Name")
