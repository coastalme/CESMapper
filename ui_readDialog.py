# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_readDialog.ui'
#
# Created: Mon Jul 20 16:05:06 2015
#      by: PyQt4 UI code generator 4.9.4
#
# WARNING! All changes made in this file will be lost!

from .compat import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8

    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_readDialog(object):
    def setupUi(self, readDialog):
        readDialog.setObjectName(_fromUtf8("readDialog"))
        readDialog.setWindowModality(QtCore.Qt.ApplicationModal)
        readDialog.resize(350, 155)
        readDialog.setMinimumSize(QtCore.QSize(350, 155))
        readDialog.setMaximumSize(QtCore.QSize(350, 155))
        readDialog.setSizeGripEnabled(False)
        readDialog.setModal(True)
        self.input = QtGui.QLineEdit(readDialog)
        self.input.setGeometry(QtCore.QRect(10, 40, 251, 21))
        self.input.setReadOnly(True)
        self.input.setObjectName(_fromUtf8("input"))
        self.label = QtGui.QLabel(readDialog)
        self.label.setGeometry(QtCore.QRect(20, 10, 161, 16))
        self.label.setObjectName(_fromUtf8("label"))
        self.inputButton = QtGui.QPushButton(readDialog)
        self.inputButton.setGeometry(QtCore.QRect(270, 40, 75, 23))
        self.inputButton.setObjectName(_fromUtf8("inputButton"))
        self.cancelButton = QtGui.QPushButton(readDialog)
        self.cancelButton.setGeometry(QtCore.QRect(240, 100, 101, 32))
        self.cancelButton.setObjectName(_fromUtf8("cancelButton"))
        self.OKButton = QtGui.QPushButton(readDialog)
        self.OKButton.setGeometry(QtCore.QRect(120, 100, 114, 32))
        self.OKButton.setObjectName(_fromUtf8("OKButton"))

        self.retranslateUi(readDialog)
        QtCore.QMetaObject.connectSlotsByName(readDialog)

    def retranslateUi(self, readDialog):
        readDialog.setWindowTitle(_translate("readDialog", "Coastal Mapping Tool", None))
        self.label.setText(_translate("readDialog", "Load CESM map file:", None))
        self.inputButton.setText(_translate("readDialog", "Browse", None))
        self.cancelButton.setText(_translate("readDialog", "Cancel", None))
        self.OKButton.setText(_translate("readDialog", "OK", None))

