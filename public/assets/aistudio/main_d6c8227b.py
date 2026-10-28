# -*- coding: utf-8 -*-
"""Точка входа для G-Code редактора Mach3."""

import sys
from PyQt5.QtWidgets import QApplication
from gcode_editor.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
