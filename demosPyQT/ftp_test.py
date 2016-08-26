#!/usr/bin/env python

# autor: bosito7 (bosito7@gmail.com)

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import QtNetwork
from PyQt4.QtCore import pyqtSlot, SIGNAL, SLOT
import sys


class myFTP(QtNetwork.QFtp):
    @pyqtSlot(int)
    def connectionStateChanged(self, state):
        print "Current Connection State is: "
        print state


def main():
    app = QtGui.QApplication(sys.argv)
    ftp = myFTP()
    ftp.connectToHost("ftp.qt.nokia.com");

    ftp.connect(ftp, SIGNAL("stateChanged(int)"), ftp, SLOT("connectionStateChanged(int)"));
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
