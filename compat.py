from qgis.PyQt import QtCore, QtGui, QtWidgets


_WIDGET_ALIASES = (
    "QApplication",
    "QButtonGroup",
    "QDialog",
    "QGroupBox",
    "QLabel",
    "QLayout",
    "QLineEdit",
    "QPushButton",
    "QRadioButton",
    "QSizePolicy",
    "QVBoxLayout",
    "QWidget",
)


for _alias in _WIDGET_ALIASES:
    if not hasattr(QtGui, _alias):
        setattr(QtGui, _alias, getattr(QtWidgets, _alias))


if not hasattr(QtGui.QApplication, "UnicodeUTF8"):
    QtGui.QApplication.UnicodeUTF8 = -1


__all__ = ["QtCore", "QtGui", "QtWidgets"]