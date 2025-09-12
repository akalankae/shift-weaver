#!/usr/bin/env python
# gui.py
# Graphical User Interface for roster synchronizer program.

import hashlib
import json
import random
import sys
from pathlib import Path
from typing import final, override

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QShowEvent
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QMessageBox,
)


@final
class LoginWindow(QWidget):
    """
    User enters his/her icloud account credentials at Login Window.
    Caller provides a dictionary `login_info` to put user credentials into.
    """

    def __init__(self, userdata: dict[str, str]):
        super().__init__()
        self.userdata = userdata  # dict to store user credentials

        self.setWindowTitle("Login Window")
        self.setMinimumWidth(360)

        heading = QLabel("iCloud User Credentials", self)
        heading.setFont(QFont("Times", 16, 500, True))
        username_lbl = QLabel("Username:", self)
        username_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.username_entry = QLineEdit(self)
        password_lbl = QLabel("Password:", self)
        password_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.password_entry = QLineEdit(self)
        save_creds_cb = QCheckBox("Save Credentials", self)
        enter_btn = QPushButton("Enter", self)
        enter_btn.clicked.connect(self.get_user_credentials)
        quit_btn = QPushButton("Quit", self)
        quit_btn.clicked.connect(self.close)

        # visually seperate action buttons from form
        separator = QFrame(self)
        separator.setFrameShape(QFrame.Shape.NoFrame)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setLineWidth(1)
        separator.setMidLineWidth(0)
        separator.setFixedHeight(20)

        root_layout = QVBoxLayout(self)
        cred_field_layout = QGridLayout()
        cred_field_layout.addWidget(username_lbl, 0, 0)
        cred_field_layout.addWidget(self.username_entry, 0, 1)
        cred_field_layout.addWidget(password_lbl, 1, 0)
        cred_field_layout.addWidget(self.password_entry, 1, 1)
        button_layout = QHBoxLayout()
        button_layout.addWidget(quit_btn)
        button_layout.addWidget(enter_btn)

        root_layout.addWidget(heading, 0, Qt.AlignmentFlag.AlignHCenter)
        root_layout.addLayout(cred_field_layout, 0)
        root_layout.addWidget(save_creds_cb, 0, Qt.AlignmentFlag.AlignHCenter)
        root_layout.addWidget(separator)
        root_layout.addLayout(button_layout, 0)

        self.setLayout(root_layout)

    def get_user_credentials(self):
        """
        populate the userdata dictionary with user credentials.
        """
        self.userdata["username"] = self.username_entry.text().strip()
        self.userdata["password"] = self.password_entry.text().strip()
        self.close()
        return self.userdata


@final
class UploadWindow(QWidget):
    """
    User selects type of roster and roster file to upload.
    """

    def __init__(self, userdata: dict[str, str]):
        super().__init__()
        self.userdata = userdata  # dict to put info about choice of roster
        self.setWindowTitle("Upload Roster")

        heading_lbl_1 = QLabel("Select Roster Type", self)
        heading_lbl_1.setFont(QFont("Times", 14, 250, True))
        term_roster_cbox = QCheckBox("Term Roster", self)
        week_roster_cbox = QCheckBox("Week Roster", self)

        roster_type = QButtonGroup(self)
        roster_type.addButton(term_roster_cbox, 0)
        roster_type.addButton(week_roster_cbox, 1)
        roster_type.idClicked.connect(self.select_roster_type)

        heading_lbl_2 = QLabel("Select Roster File", self)
        heading_lbl_2.setFont(QFont("Times", 14, 250, True))
        self.upload_btn = QPushButton("Upload", self)
        self.upload_btn.setEnabled(False)
        self.upload_btn.clicked.connect(self.select_roster)
        self.enter_btn = QPushButton("Enter", self)
        self.enter_btn.setEnabled(False)
        self.enter_btn.clicked.connect(self.upload_roster)
        self.quit_btn = QPushButton("Quit", self)
        self.quit_btn.clicked.connect(self.close)

        # visually seperate action buttons from form
        separator = QFrame(self)
        separator.setFrameShape(QFrame.Shape.NoFrame)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setLineWidth(1)
        separator.setMidLineWidth(0)
        separator.setFixedHeight(20)

        selection_layout = QGridLayout()
        selection_layout.setHorizontalSpacing(40)
        selection_layout.addWidget(heading_lbl_1, 0, 0, 1, 1)
        selection_layout.addWidget(heading_lbl_2, 0, 1, 1, 1)
        selection_layout.addWidget(
            term_roster_cbox, 1, 0, 1, 1, Qt.AlignmentFlag.AlignHCenter
        )
        selection_layout.addWidget(
            week_roster_cbox, 2, 0, 1, 1, Qt.AlignmentFlag.AlignHCenter
        )
        selection_layout.addWidget(self.upload_btn, 1, 1, 2, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.quit_btn, 0, Qt.AlignmentFlag.AlignRight)
        btn_layout.addStretch()
        btn_layout.addWidget(self.enter_btn, 0, Qt.AlignmentFlag.AlignRight)

        root_layout = QVBoxLayout(self)
        root_layout.addLayout(selection_layout, 0)
        root_layout.addWidget(separator)
        root_layout.addLayout(btn_layout, 0)

    @override
    def showEvent(self, a0: QShowEvent | None):
        """
        Manually resize "Enter" and "Quit" buttons, so that they don't end up too
        small compared to "Upload" button.
        """
        upload_btn_height = self.upload_btn.height()
        upload_btn_width = self.upload_btn.width()
        self.enter_btn.setMinimumSize(upload_btn_width, upload_btn_height // 2)
        self.quit_btn.setMinimumSize(upload_btn_width, upload_btn_height // 2)
        super().showEvent(a0)

    def select_roster_type(self, checkbox_id: int):
        self.roster_type = ("term", "week")[checkbox_id]
        self.upload_btn.setEnabled(True)

    def select_roster(self):
        """
        Upload the roster user wants to enter in the calendar.
        """
        filedialog = QFileDialog(self, "Select Roster File")
        filedialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        # filedialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        filedialog.setViewMode(QFileDialog.ViewMode.Detail)

        if filedialog.exec():
            selected_file = filedialog.selectedFiles()[0]
            self.roster_path = Path(selected_file)
            self.upload_btn.setText(self.roster_path.name)
            self.upload_btn.adjustSize()

        if self.roster_path.is_file():
            self.enter_btn.setEnabled(True)
        else:
            self.enter_btn.setEnabled(False)
            print(f"Roster file: {self.roster_path} doesn't exist!")

    def upload_roster(self):
        """
        Upload shifts from the selected roster to iCloud calendar.
        """
        print(f"Uploading roster file: {self.roster_path}")
        self.close()


@final
class NameSelectWindow(QWidget):
    """
    User selects his/her name in the roster.
    """

    def __init__(self, name_list: list[str]):
        super().__init__()
        self.setWindowTitle("Select Your Name")
        self.setMinimumWidth(360)

        heading_lbl = QLabel("Select Your Name", self)
        heading_lbl.setFont(QFont("Times", 16, 500, True))

        back_btn = QPushButton("Go Back", self)
        enter_btn = QPushButton("Enter", self)
        enter_btn.setMinimumWidth(160)
        quit_btn = QPushButton("Quit", self)
        quit_btn.setMinimumWidth(160)
        names_cbox = QComboBox(self)
        names_cbox.addItems(name_list)
        names_cbox.setMaxVisibleItems(12)
        save_creds_cb = QCheckBox("Remember Me", self)

        # visually seperate action buttons from form
        separator = QFrame(self)
        separator.setFrameShape(QFrame.Shape.NoFrame)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setLineWidth(1)
        separator.setMidLineWidth(0)
        separator.setFixedHeight(20)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(quit_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(enter_btn)

        root_layout = QVBoxLayout(self)
        root_layout.addWidget(back_btn, 0, Qt.AlignmentFlag.AlignLeft)
        root_layout.addWidget(heading_lbl, 0, Qt.AlignmentFlag.AlignHCenter)
        root_layout.addWidget(names_cbox, 0, Qt.AlignmentFlag.AlignHCenter)
        root_layout.addWidget(save_creds_cb, 0, Qt.AlignmentFlag.AlignHCenter)
        root_layout.addWidget(separator)
        root_layout.addLayout(btn_layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    data = {}
    win_1 = LoginWindow(data)
    win_1.show()
    win_2 = UploadWindow(data)
    win_2.show()

    FILE = "data/names.txt"  # file with list of random full names
    NUM_RANDOM_NAMES = 50  # number of names to show in ComboBox
    try:
        data = Path(FILE).read_text("utf-8")
        name_list = [
            s.title() for s in random.sample(data.splitlines(), NUM_RANDOM_NAMES)
        ]
    except FileNotFoundError:
        sys.stderr.write(f"Could not find file: {FILE}")
        name_list = [
            "Jack Napier",
            "Jill Taylor",
            "Robert Pattingson",
            "Anne Hathaway",
            "Patrick Jane",
        ]
    win_3 = NameSelectWindow(name_list)
    win_3.show()

    sys.exit(app.exec())
