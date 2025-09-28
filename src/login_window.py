#!/usr/bin/env python
# login_window.py
# Possible login window for ShiftWeaver application
# Has following input fields (QLineEdit):
# - username
# - password (checkbox to hide/reveal password)
# - employee ID
# - employer name
# Enter or Submit button to move to next


import sys
from typing import final

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_MINIMUM_PASSWORD_LENGTH = 20


@final
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login to iCloud")

        # window heading
        heading = QLabel("User Credentials", self)
        heading.setFont(QFont("Arial", 18))
        heading.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        # username
        username_entry = QLineEdit(self)
        username_entry.setPlaceholderText("username@icloud.com")

        # password + reveal button
        self.password_entry = QLineEdit(self)
        self.password_entry.setPlaceholderText("********")
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        font_metrics = self.password_entry.fontMetrics()
        min_password_entry_pxl = font_metrics.horizontalAdvance(
            "W" * _MINIMUM_PASSWORD_LENGTH
        )
        self.password_entry.setMinimumWidth(min_password_entry_pxl)
        reveal_cb = QCheckBox("Reveal password", self)
        reveal_cb.checkStateChanged.connect(self.hide_or_reveal_password)
        password_layout = QVBoxLayout()
        password_layout.addWidget(self.password_entry)
        password_layout.addWidget(reveal_cb)

        # employee ID
        employee_id_entry = QLineEdit(self)
        employee_id_entry.setPlaceholderText("60316064")

        # employer name
        employer_name_entry = QLineEdit(self)
        employer_name_entry.setPlaceholderText("SWSLHD")

        # submit button
        submit_btn = QPushButton("Submit", self)
        submit_btn.clicked.connect(self.read_user_data)

        # form layout
        form_layout = QFormLayout(self)
        form_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        form_layout.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
        )
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        form_layout.addRow(heading)
        form_layout.addRow("Username", username_entry)
        form_layout.addRow("Password", password_layout)
        form_layout.addRow("Employee ID", employee_id_entry)
        form_layout.addRow("Employer", employer_name_entry)
        form_layout.addRow(submit_btn)

        self.setLayout(form_layout)

    def read_user_data(self):
        pass

    def hide_or_reveal_password(self, checkstate):
        if checkstate == Qt.CheckState.Checked:
            self.password_entry.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)


app = QApplication(sys.argv)
main = MainWindow()
main.show()
sys.exit(app.exec())
