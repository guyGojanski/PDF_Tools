from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from assets.config import *


class HeaderBar(QWidget):
    back_clicked = pyqtSignal()

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFixedHeight(HEADER_BAR_HEIGHT)
        self._init_ui(title)

    def _init_ui(self, title):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        self.back_button = QPushButton("menu")
        self.back_button.setObjectName("BackNavButton")
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_button.setFixedSize(BACK_BUTTON_SIZE, BACK_BUTTON_SIZE)
        self.back_button.clicked.connect(self.back_clicked.emit)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("ScreenTitleLabel")
        layout.addWidget(self.back_button)
        layout.addStretch()
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addSpacing(50)
