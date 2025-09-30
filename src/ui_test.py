#!/usr/bin/env python
# ui_test.py
# Test Graphical user interface for the program

import sys
from ui import MainWindow
from PyQt6.QtWidgets import QApplication


app = QApplication(sys.argv)

main_window = MainWindow()
main_window.show()

sys.exit(app.exec())
