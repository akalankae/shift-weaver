#!/usr/bin/env python
# ui.py
# Graphical user interface for the program

import atexit
import pickle
import sys
import time
from collections.abc import Sequence
from datetime import datetime
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import final

import pandas as pd
from caldav import calendarobjectresource
from caldav.davclient import get_davclient
from caldav.lib.error import (
    AuthorizationError,
    ConsistencyError,
    NotFoundError,
    PutError,
)
from pandas.core.frame import DataFrame
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
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
)

from calendar_handler import get_calendar_list, get_shifts_from_calendar
from shift import Shift
from term_roster_parser import TermRosterParser

DEFAULT_LOG_FILE = "/tmp/shift-weaver.log"
if len(sys.argv) > 1:
    log_file = Path(sys.argv[1]).expanduser().resolve()
    if log_file.exists() and log_file.is_file():
        LogFile = log_file.open("wt", encoding="utf8")
    else:
        LogFile = Path(DEFAULT_LOG_FILE).open("wt", encoding="utf8")
else:
    LogFile = Path(DEFAULT_LOG_FILE).open("wt", encoding="utf8")


@atexit.register
def close_logfile():
    LogFile.close()
    print(f"Closed Logfile: {LogFile.name}")


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
        self.worksheets: dict[str, DataFrame] = dict()  # worksheet_name->DataFrame
        self.roster: DataFrame = DataFrame()  # DataFrame that has excel worksheet

        # SIGNAL-SLOT for Login
        self.login_window = LoginWindow(self.USER_DATA_DIR)
        self.login_window.login_success.connect(self.login)

        self.calendar_picker_window = None
        self.roster_uploader_window = None
        self.name_selector_window = None
        self.worksheet_select_window = None

        self.root = QStackedWidget()
        self.root.addWidget(self.login_window)

        self.setCentralWidget(self.root)

    def login(self, data: dict[str, str]):
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
            # SIGNAL-SLOT for Picking Preferred Calendar
            self.calendar_picker_window = CalendarPickerWindow(calendars)
            self.calendar_picker_window.calendar_found.connect(
                self.get_preferred_calendar
            )

            self.root.addWidget(self.calendar_picker_window)
            self.root.setCurrentWidget(self.calendar_picker_window)

    def get_preferred_calendar(self, calendar_info: dict):
        """
        Slot for the signal CalendarPickerWindow.calendar_found.
        Takes a dictionary with 2 keys.
        * name(str): name of the calendar to use
        * new_calendar(bool): create new calendar or not?
        Finishes off by launching the window to select the roster file.
        """
        self.calendar_name = calendar_info["name"]  # string
        self.create_calendar = calendar_info["new_calendar"]  # bool
        self.upload_roster()

    def upload_roster(self):
        """
        Launches the window to select the roster file to read and upload to the server.
        Selects both roster type: "term" or "week" roster AND path to excel roster file.
        """
        self.roster_upload_window = RosterUploaderWindow()
        self.roster_upload_window.roster_received.connect(self.get_roster_info)
        self.root.addWidget(self.roster_upload_window)
        self.root.setCurrentWidget(self.roster_upload_window)

    def get_roster_info(self, roster_info: dict[str, str]):
        """
        Slot for RosterUploaderWindow.roster_recieved signal.
        Takes one dictionary parameter with 2 keys.
        * type(str): type of uploaded roster - term or week
        * file(str): file path to parsed roster file (excel file)
        """
        self.roster_type = roster_info["type"]
        self.roster_file = roster_info["file"]

        if self.roster_type == "term":
            self.parse_term_roster()
        elif self.roster_type == "week":
            print("Not Implemented Yet")
            raise NotImplementedError("Week roster is not implemented yet.")

    def parse_term_roster(self):
        """
        Reads the term roster and parses it into a TermRosterParser object.
        Parsed roster has the ability to get the shifts for any user for the term.
        """
        if self.roster_file is None:
            sys.stderr.write("None is not a valid roster file\n")
            return

        # Try to get the last active worksheet from excel file, if we cannot find this
        # read all the worksheets and ask the user to select the one he/she wants
        t0 = time.perf_counter()  # Dbg

        with pd.ExcelFile(self.roster_file, engine="openpyxl") as xl:
            try:
                active_sheet = xl.book.active.title
            except AttributeError:
                QMessageBox.information(
                    self,
                    "Active Worksheet Not Found",
                    """Cannot find the active (last saved) worksheet in the excel file.<br>
                    We have to read all sheets and you have to pick one from them!
                    (NOTE: This will take some time)""",
                )
                self.worksheets = pd.read_excel(
                    self.roster_file, engine="openpyxl", sheet_name=None
                )

                dt = time.perf_counter() - t0  # Dbg
                sys.stderr.write(f"""
            Reading all worksheets of excel file took {dt:.3f} seconds
            """)

                self.worksheet_select_window = WorksheetSelectWindow(
                    list(sorted(self.worksheets.keys()))
                )
                self.worksheet_select_window.worksheet_selected.connect(
                    self.select_worksheet
                )

                self.root.addWidget(self.worksheet_select_window)
                self.root.setCurrentWidget(self.worksheet_select_window)
            else:
                dt = time.perf_counter() - t0  # Dbg
                sys.stderr.write(f"""
            Reading the active worksheet "{self.roster_file}" took {dt:.3f} seconds
            """)
                self.roster = pd.read_excel(xl, active_sheet)
                self.parser = TermRosterParser(self.roster)
                self.select_username()

    def select_worksheet(self, worksheet_name: str):
        """
        This method is only executed if we cannot find the active worksheet.
        """
        roster = self.worksheets.get(worksheet_name)
        if roster is None:
            raise ValueError("worksheet is empty")
        self.roster = roster
        self.parser = TermRosterParser(roster)
        self.select_username()

    def select_username(self):
        if self.parser is None:
            raise ValueError("parsed worksheet is empty")

        names = self.parser.name_to_row.keys()
        self.name_select_window = NameSelecterWindow(list(names))
        self.name_select_window.name_selected.connect(self.update_calendar)

        self.root.addWidget(self.name_select_window)
        self.root.setCurrentWidget(self.name_select_window)

    # TODO: Need to break up this BIG monolithic method
    def update_calendar(self, username: str):
        """
        Use all the user preferences and parsed roster to update the relevant calendar
        in icloud caldav server.
        """
        if self.parser is None:
            sys.stderr.write("Invalid Term Roster Parser\n")
            return

        updated_shifts: list[Shift] = []  # shifts for the term from roster (excel)

        user_row = self.parser.name_to_row[username]
        valid_dates = self.roster.loc[self.parser.date_row].map(
            lambda o: isinstance(o, datetime)
        )
        dates = self.roster.loc[self.parser.date_row].loc[valid_dates]  # pyright: ignore
        shift_labels = self.roster.loc[user_row].loc[valid_dates]  # pyright: ignore

        # remove non-dates from dates list, whitespace from shift labels and
        # clean them up before mapping dates to the shifts (date->shift_label)
        # NOTE: following for loop ensures that the number of valid dates and number of
        # valid labels are equal. If we removed invalid dates earlier, it would have
        # made list of dates shorter than list of shift_labels.
        for dt, shift_label in zip(dates, shift_labels):
            if (
                pd.notna(shift_label)
                and isinstance(shift_label, str)  # a string
                and (shift_label := shift_label.strip())  # not empty/whitespace only
                and shift_label.upper() not in ("OFF")  # `OFF` days are just empty
            ):
                _shift = Shift(dt.date(), shift_label)
                print(f"{_shift}\n")
                updated_shifts.append(_shift)

        # TODO: In case wrong year and/or month may have been entered by the clerk, need
        # to give the user the option to change wrong dates.
        # NOTE: We need all dates for the TERM in roster, not for the user only
        min_date = min(dates)
        max_date = max(dates)

        msg = f"<p>Roster from {min_date.date()} to {max_date.date()} has {len(updated_shifts)} shifts<p>"
        QMessageBox.about(self, "About Roster", msg)
        sys.stderr.write(f"{msg}\n")

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

        # TODO: following comment needs updating (probably removal?)
        # A WORD ABOUT LOGIC: caldav.Event.save() can "update" as well as create new
        # events. If a shift is not in the new roster, we remove it from calendar. If it
        # is in the new roster, it's SEQUENCE property is incremented (ie. it will be
        # updated) in the icloud calendar.

        old_shifts: list[calendarobjectresource.Event] = get_shifts_from_calendar(
            target_calendar, min_date, max_date
        )
        # If there are any shifts in the current calendar in icloud, check them against
        # shifts in uploaded roster. If new roster does not have same shifts, then
        # delete them from icloud calendar.
        if len(old_shifts) > 0:
            print(f"Found {len(old_shifts)} shifts in current roster")
            if LogFile is not None:
                LogFile.write(f"Found {len(old_shifts)} shifts in current roster\n")

            # check for differences between old and new and delete set(old) - set(new)
            outdated_shifts: list[calendarobjectresource.Event] = []
            for shift in old_shifts:
                if shift.icalendar_component not in updated_shifts:
                    outdated_shifts.append(shift)
            print("\nOutdated Shifts")
            for shift in outdated_shifts:
                if LogFile is not None:
                    LogFile.write(str(shift))
                shift.delete()  ## BLOCKING !!!
        else:
            print(
                f"No shifts were found for the time period from {min_date} to {max_date}"
            )

        # collect all shifts in uploaded new roster that are not in icloud calendar
        new_shifts: list[Shift] = []
        for new_shift in updated_shifts:
            for old_shift in old_shifts:
                old_shift_uid = old_shift.icalendar_component.get("UID")
                if new_shift.uid == old_shift_uid:
                    print(
                        f"New shift: {new_shift.start} {new_shift.get('summary')}\n"
                        f"Old shift: {old_shift.component.dtstart} {old_shift.component.get('summary')}"
                    )
                    break
            else:
                new_shifts.append(new_shift)

        msg = f"{len(new_shifts)} new shifts were found from {min_date.date()} to {max_date.date()} in {target_calendar.name}"
        print(msg)
        LogFile.write(f"{msg}\n")

        # insert all shifts in the new roster to calendar (update existing ones)
        # threads = []
        # Gather outcome of writing to calendar (caldav.Calendar.save_event()). If
        # writing successful TRUE, if failed FALSE. Position in the list tallys with
        # position in the list of shifts in `new_shifts` (ie. they're parellel lists)
        success_count = 0
        fail_count = 0
        with ThreadPool(len(new_shifts)) as pool:
            args = [
                (
                    target_calendar,
                    {
                        "ical": shift.to_ical(),
                        "no_create": False,
                        "no_overwrite": False,
                    },
                )
                for shift in new_shifts
            ]
            results = pool.starmap(self.__save_calendar_event, args)
            result_list = list(results)
            success_count = result_list.count(True)
            fail_count = result_list.count(False)

        LogFile.write(f"""
    * Successfully written: {success_count} shifts
    * Failed to write: {fail_count} shifts
    """)
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
    def __save_calendar_event(calendar, kwargs_dict) -> bool:
        try:
            calendar.save_event(**kwargs_dict)
        except (ConsistencyError, PutError):
            return False
        else:
            return True


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

        # Choose one from existing calendars: checkbox + combobox
        self.pick_cal_cb = QCheckBox("Select existing calendar")
        self.pick_cal_combo = QComboBox()
        self.pick_cal_combo.addItems(calendars)

        # Create a new calendar: checkbox + lineedit
        self.new_cal_cb = QCheckBox("Create a new calendar")
        self.new_cal_entry = QLineEdit()

        # If list of calendars is empty, disable picking existing calendar and check
        # creating a new calendar. If not just check picking existing calendar.
        if len(calendars) < 1:
            self.pick_cal_cb.setEnabled(False)
            self.pick_cal_combo.setEnabled(False)
            self.new_cal_cb.setChecked(True)
        else:
            self.new_cal_cb.setChecked(False)
            self.new_cal_entry.setEnabled(False)

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

        # Week roster upload is not yet implemented
        self.week_cb.checkStateChanged.connect(self.not_implemented)

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

    def not_implemented(self, checkState):
        """
        Automatically disable checkbox for week roster if user clicks this, as this
        functionality is not yet implemented.
        """
        if self.week_cb.checkState() == Qt.CheckState.Checked:
            QMessageBox.information(
                self, "Not Implemented", "Week roster uploading is not yet implemented"
            )
            self.week_cb.setEnabled(False)

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


@final
class WorksheetSelectWindow(QGroupBox):
    """
    Allow the user to select the desired excel worksheet from workbook with many.
    NOTE: Unlike openpyxl.workbook.Workbook.active, pandas does not have a way to
    reliably do this.
    """

    worksheet_selected = pyqtSignal(str)

    def __init__(self, file_list: Sequence[str], *args, **kwargs):
        super().__init__("Select the excel worksheet you want")
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        heading = QLabel("What's the name of the roster you want?")
        self.combobox = QComboBox()
        self.combobox.addItems(file_list)
        self.submit = QPushButton("Submit")
        self.submit.clicked.connect(self.select_worksheet)

        vbox = QVBoxLayout()
        vbox.addWidget(heading)
        vbox.addWidget(self.combobox)
        vbox.addWidget(self.submit)
        self.setLayout(vbox)

    def select_worksheet(self):
        worksheet_name = self.combobox.currentText()
        self.worksheet_selected.emit(worksheet_name)
