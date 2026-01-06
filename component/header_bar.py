from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal


class HeaderBar(QWidget):
    back_clicked = pyqtSignal()

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFixedHeight(70)
        self._init_ui(title)

    def _init_ui(self, title):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)

        self.back_btn = QPushButton("menu")
        self.back_btn.setObjectName("BackButton")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setFixedSize(50, 50)
        self.back_btn.clicked.connect(self.back_clicked.emit)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("MergeTitle")

        layout.addWidget(self.back_btn)
        layout.addStretch()
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addSpacing(50)
