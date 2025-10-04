#!/usr/bin/env python
# ui.py
# Graphical user interface for the program

import pickle
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import final
import threading
import time

from caldav import calendarobjectresource
from icalendar.cal import Event
from caldav.davclient import get_davclient
from caldav.lib.error import AuthorizationError, ConsistencyError, NotFoundError
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from calendar_handler import get_calendar_list, get_shifts_from_calendar
from shift import Shift
from term_roster_parser import TermRosterParser


LOG_FILE = None

if len(sys.argv) > 1:
    log_file = Path(sys.argv[1]).expanduser().resolve()
    if log_file.exists() and log_file.is_file():
        LOG_FILE = log_file.open("utf8")


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

        self.user_data: dict[str, str] | None = None  # credentials & user info
        self.calendar_name: str | None = None  # user's preferred calendar
        self.create_calendar: bool = False  # Whether to create a new calendar or not
        self.roster_file: str | None = None  # path of roster file
        self.roster_type: str | None = None  # "term" or "week" roster
        self.parser: TermRosterParser | None = None  # parsed roster object
        self.name_in_roster: str | None = None  # Name for the user in the roster

        self.login_window = LoginWindow(self.USER_DATA_DIR)
        self.login_window.login_success.connect(self.handle_login)

        self.calendar_picker_window = None
        self.roster_uploader_window = None
        self.name_selector_window = None

        self.root = QStackedWidget()
        self.root.addWidget(self.login_window)

        self.setCentralWidget(self.root)

    def handle_login(self, data: dict[str, str]):
        """
        After user submits the user credentials (and other information) in Login
        window, icloud's CalDAV server is queried with those credentials for a
        list of existing calendars. Then they are displayed for user to select
        one from. Or user can choose to create a new calendar.
        This method creates the window for selecting a calendar and pops it onto
        the main window.
        """
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
            self.calendar_picker_window.calendar_found.connect(
                self.get_preferred_calendar
            )

            self.root.addWidget(self.calendar_picker_window)
            self.root.setCurrentWidget(self.calendar_picker_window)

    def get_preferred_calendar(self, calendar_info: dict):
        self.calendar_name = calendar_info["name"]  # string
        self.create_calendar = calendar_info["new_calendar"]  # bool
        self.upload_roster()

    def upload_roster(self):
        self.roster_upload_window = RosterUploaderWindow()
        self.roster_upload_window.roster_received.connect(self.get_roster_info)
        self.root.addWidget(self.roster_upload_window)
        self.root.setCurrentWidget(self.roster_upload_window)

    def get_roster_info(self, roster_info: dict[str, str]):
        self.roster_type = roster_info["type"]
        self.roster_file = roster_info["file"]

        if self.roster_type == "term":
            self.parse_term_roster()
        elif self.roster_type == "week":
            print("Not Implemented Yet")

    def parse_term_roster(self):
        if self.roster_file is None:
            sys.stderr.write("None is not a valid roster file\n")
            return

        t0 = time.perf_counter() # Dbg
        self.parser = TermRosterParser(self.roster_file)
        t1 = time.perf_counter()
        names = self.parser.name_to_row.keys()
<<<<<<< HEAD
<<<<<<< HEAD
        # ? Disable select name combobox if `names` is empty
=======

        dt2 = time.perf_counter() - t1
        sys.stderr.write(f"""
    Creating `TermRosterParser` took {t1-t0:.3f} seconds
    .keys() invocation on Parser.name_to_row took {dt2:.3f} seconds
    """)

>>>>>>> 4674977 (wip(multithreading): make writing to server multi-threaded for efficiency)
=======
        # ? Disable select name combobox if `names` is empty
>>>>>>> ea10262 (fix: get deleting existing shifts to work)
        self.name_select_window = NameSelecterWindow(list(names))
        self.name_select_window.name_selected.connect(self.update_calendar)

        self.root.addWidget(self.name_select_window)
        self.root.setCurrentWidget(self.name_select_window)

    def update_calendar(self, username: str):
        """
        Update the relevant calendar in icloud.
        """
        if self.parser is None:
            sys.stderr.write("Invalid Term Roster Parser\n")
            return

        roster = self.parser.roster  # openpyxl `Worksheet`
        user_row = self.parser.name_to_row[username]  # name string: row number (int)
        date_row = self.parser.date_row  # row number for dates row (int)
        name_col = self.parser.name_column  # column number for user (int)

        shifts: list[Shift] = []  # List of shifts for the term
        dates = [cell.value for cell in roster[date_row][name_col:]]
        shift_labels = [cell.value for cell in roster[user_row][name_col:]]

        # remove non-dates from dates list, whitespace from shift labels and
        # clean them up before mapping dates to the shifts (date->shift_label)
        # NOTE: following for loop ensures that the number of valid dates and number of
        # valid labels are equal. If we removed invalid dates earlier, it would have
        # made list of dates shorter than list of shift_labels.
        for dt, shift_label in zip(dates, shift_labels):
            if isinstance(dt, datetime) and (
                (shift_label is not None)
                and isinstance(shift_label, str)  # a string
                and (shift_label := shift_label.strip())  # not empty/whitespace only
                and shift_label.upper() not in ("OFF")  # `OFF` days are just empty
            ):
                shifts.append(Shift(dt.date(), shift_label))

        # TODO: In case wrong year and/or month may have been entered by the clerk, need
        # to give the user the option to change wrong dates.
        # NOTE: We need all dates for the TERM in roster, not for the user only
        all_dates = [value for value in dates if isinstance(value, datetime)]
        min_date = min(all_dates)
        max_date = max(all_dates)
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> ea10262 (fix: get deleting existing shifts to work)
        QMessageBox.about(
            self,
            "About Roster",
            f"""<p>Roster from {min_date.date()} to {max_date.date()}<br>
            Roster has {len(shifts)} shifts<p>""",
        )
<<<<<<< HEAD
=======
        msg = f"<p>Roster from {min_date.date()} to {max_date.date()} has {len(shifts)} shifts<p>"
        QMessageBox.about(self, "About Roster", msg)
        sys.stderr.write(f"{msg}\n")
>>>>>>> 4674977 (wip(multithreading): make writing to server multi-threaded for efficiency)
=======
>>>>>>> ea10262 (fix: get deleting existing shifts to work)

        # Get calendar events in the calendar of user's choosing, for the time period
        # that have been put there by our application. We identify this by its
        # "X-PUBLISHED-BY" property.
        if self.user_data is None:
            return  # We should not get here (just for type-checker)

        try:
            with get_davclient(
                url="https://caldav.icloud.com/",
                username=self.user_data["username"],
                password=self.user_data["password"],
            ) as client:
                principal = client.principal()
                if self.create_calendar:
                    target_calendar = principal.make_calendar(self.calendar_name)
                    print(f"Created new calendar: {self.calendar_name}")
                else:
                    target_calendar = principal.calendar(self.calendar_name)
        except NotFoundError as err:
            sys.stderr.write(f'Cannot find "{self.calendar_name}" calendar\n')
            sys.stderr.write(f"{err}\n")
            return
        except AuthorizationError as err:
            sys.stderr.write("Username and/or password is wrong\n")
            sys.stderr.write(f"{err}\n")
            return
        except Exception as err:
            sys.stderr.write(f"Unknown error: {err}\n")
            return

        # A WORD ABOUT LOGIC: caldav.Event.save() can "update" as well as create new
        # events. If a shift is not in the new roster, we remove it from calendar. If it
        # is in the new roster, it's SEQUENCE property is incremented (ie. it will be
        # updated) in the icloud calendar.

        curr_shifts: list[calendarobjectresource.Event] = get_shifts_from_calendar(
            target_calendar, min_date, max_date
        )
        if len(curr_shifts) > 0:
            print(f"Found {len(curr_shifts)} shifts in roster")

            # check for differences between old and new and delete set(old) - set(new)
            outdated_shifts: list[calendarobjectresource.Event] = []
            for shift in curr_shifts:
                if shift.icalendar_component not in shifts:
                    outdated_shifts.append(shift)
            for shift in outdated_shifts:
                if LOG_FILE is not None:
                    LOG_FILE.write(shift.data)
                shift.delete()
        else:
            print(
                f"No shifts were found for the time period from {min_date} to {max_date}"
            )

        # insert all shifts in the new roster to calendar (update existing ones)
        threads = []
        outcomes = {
            "success_count": 0,  # number of shifts that were successfully added to calendar
            "fails": [],  # shifts failed to add to calendar
        }
        for shift in shifts:
            thread = threading.Thread(
                target=self.__save_calendar_event,
                args=(target_calendar, outcomes),
                kwargs={
                    "ical": shift.to_ical(),
                    "no_create": False,
                    "no_overwrite": False,
                },
            )
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        success_count = outcomes["success_count"]
        fail_count = len(outcomes["fails"])
        if (
            QMessageBox.information(
                self,
                "Program Completed",
                f"""<p>Program was completed successfully<p>
             * Successfully written {success_count} shifts<br>
             * Failed to write {fail_count} shifts""",
            )
            == QMessageBox.StandardButton.Ok
        ):
            sys.exit(0)

    @staticmethod
    def __save_calendar_event(calendar, outcomes, **kwargs):
        try:
            calendar.save_event(**kwargs)
        except ConsistencyError as err:
            shift_ical = kwargs["ical"]
            outcomes["fails"].append(shift_ical)
            sys.stderr.write(f"{err}\n")
            print(
                f"Could not write shift: {shift_ical.decode('utf8').replace('\r', '')}"
            )
        else:
            outcomes["success_count"] += 1


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
        print(self.user_data)
        answer = QMessageBox.information(
            self,
            "User Credentials & Information",
            f"""<p>You Entered Following<p>
            * Username: {self.user_data["username"]}<br>
            * Password: {self.user_data["password"]}<br>
            * Employee ID: {self.user_data["id"]}<br>
            * Employer: {self.user_data["employer"]}""",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.No,
        )

        if answer == QMessageBox.StandardButton.Ok:
            print("Login successful")
            # signal to move on to next
            self.login_success.emit(self.user_data)

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

    NOTE: Emitted signal `calendar_found` has 2 pieces of information.
    1. Name of the calendar user wants to put roster into (name:str)
    2. Whether it is new calendar or not (new_calendar:bool)
    """

    calendar_found = pyqtSignal(dict)

    def __init__(self, calendars: list[str], *args, **kwargs):
        super().__init__("Select a Calendar")
        self.widget_map: dict[QAbstractButton, QWidget] = (
            dict()
        )  # map right widget to left widget in a form row

        # Choose one from existing calendars: checkbox + combobox
        self.pick_cal_cb = QCheckBox("Select existing calendar")
        self.pick_cal_cb.setChecked(True)
        self.pick_cal_combo = QComboBox()
        self.pick_cal_combo.addItems(calendars)
        self.widget_map[self.pick_cal_cb] = self.pick_cal_combo

        # Create a new calendar: checkbox + lineedit
        self.new_cal_cb = QCheckBox("Create a new calendar")
        self.new_cal_entry = QLineEdit()
        self.widget_map[self.new_cal_cb] = self.new_cal_entry

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
        calendar_data = dict()  # keys: name, new_calendar
        active_id = self.group.checkedId()
        if active_id == 1:
            calendar_data["name"] = self.new_cal_entry.text().strip()
            calendar_data["new_calendar"] = True
        elif active_id == 0:
            calendar_data["name"] = self.pick_cal_combo.currentText()
            calendar_data["new_calendar"] = False

        self.calendar_found.emit(calendar_data)

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

    roster_received = pyqtSignal(dict)

    def __init__(self, roster_dir: str | None = None, *args, **kwargs):
        super().__init__("Upload Roster")
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.roster_dir = roster_dir  # Last dir opened for uploading roster files
        self.roster_info: dict[str, str | None] = {
            "type": None,  # Type of uploading roster: term/week
            "file": None,  # String path to uploaded roster file
        }

        self.left_panel = QGroupBox("Roster Type")
        self.term_cb = QCheckBox("Term")
        self.week_cb = QCheckBox("Week")

        l_vbox = QVBoxLayout()
        l_vbox.addWidget(self.term_cb)
        l_vbox.addWidget(self.week_cb)
        self.left_panel.setLayout(l_vbox)

        self.group = QButtonGroup()
        self.group.setExclusive(True)
        self.group.addButton(self.term_cb, 0)
        self.group.addButton(self.week_cb, 1)
        self.group.idClicked.connect(self.roster_type_selected)

        self.right_panel = QGroupBox("Roster File")
        self.upload_label = QLabel("Select Roster File")
        self.upload_button = QPushButton("Upload")
        self.upload_button.setEnabled(False)
        self.upload_button.clicked.connect(self.upload_roster)

        r_vbox = QVBoxLayout()
        r_vbox.addWidget(self.upload_label)
        r_vbox.addWidget(self.upload_button)
        self.right_panel.setLayout(r_vbox)

        hbox = QHBoxLayout()
        hbox.addWidget(self.left_panel)
        hbox.addWidget(self.right_panel)

        self.submit_button = QPushButton("Submit")
        self.submit_button.setEnabled(False)
        self.submit_button.clicked.connect(self.submit_roster)

        vbox = QVBoxLayout()
        self.setLayout(vbox)
        vbox.addLayout(hbox)
        vbox.addWidget(self.submit_button)

    def roster_type_selected(self, roster_id: int):
        if roster_id == 0:
            self.roster_info["type"] = "term"
        elif roster_id == 1:
            self.roster_info["type"] = "week"
        self.upload_button.setEnabled(True)

    def upload_roster(self):
        """
        NOTE: We have not way to cancel selected roster file (self.roster_file)
        once it was selected. ? May be this not desired...
        """
        # Remember last dir from which roster file was uploaded
        starting_dir = self.roster_dir if self.roster_dir else str(Path.home())
        roster_file, file_selected = QFileDialog.getOpenFileName(
            self,
            "Select Roster File",
            starting_dir,
            "Excel Files (*.xlsx)",
            options=QFileDialog.Option.ReadOnly,
        )
        if file_selected:
            self.roster_dir = str(Path(roster_file).parent)
            self.roster_info["file"] = roster_file
            self.submit_button.setEnabled(True)
            print(f"Uploading roster {roster_file}...")

        elif self.roster_info["file"] is None:
            self.submit_button.setEnabled(False)

    def submit_roster(self):
        """
        Submit roster for parsing.
        """
        print(f"Submitting roster {self.roster_info['file']}...")
        button = QMessageBox.information(
            self,
            "Sumbitting Roster",
            f"""<p>You selected following roster file<p>
            * Type: {self.roster_info["type"]}<br>
            * File: {self.roster_info["file"]}""",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Ok,
        )
        if button == QMessageBox.StandardButton.Ok:
            # Move on to parsing the roster
            self.roster_received.emit(self.roster_info)


@final
class NameSelecterWindow(QGroupBox):
    """
    Display the names in the roster for the user to pick one.
    """

    name_selected = pyqtSignal(str)

    def __init__(self, name_list: Sequence[str], *args, **kwargs):
        super().__init__("Select User Name")
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        heading = QLabel("Select your name in the roster")
        self.submit_button = QPushButton("Submit")
        self.submit_button.setEnabled(False)
        self.submit_button.clicked.connect(self.submit_name)
        self.names_combo = QComboBox()
        self.names_combo.addItems(sorted(name_list))
        self.names_combo.activated.connect(lambda: self.submit_button.setEnabled(True))

        vbox = QVBoxLayout()
        vbox.addWidget(heading)
        vbox.addWidget(self.names_combo)
        vbox.addWidget(self.submit_button)
        self.setLayout(vbox)

    def submit_name(self):
        selected_name = self.names_combo.currentText()
        print(f"You selected {selected_name}")
        self.name_selected.emit(selected_name)
