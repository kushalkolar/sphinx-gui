#!/usr/bin/env python
import sys

from PyQt5 import QtWidgets

from window import MainWindow

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.setup_app()
    window.show()
    sys.exit(app.exec_())
