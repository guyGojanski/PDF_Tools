import os
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal
from PyQt6.QtGui import QDrag, QPixmap, QIcon
from component.toolsForPDF import (
    get_pdf_thumbnail,
    calculate_rotation,
    truncate_filename,
)
from assets.config import *


class FileCard(QFrame):
    delete_requested = pyqtSignal(object)
    rotate_requested = pyqtSignal(object)

    def __init__(self, item_data, index=0, click_to_toggle: bool = False):
        super().__init__()
        self.setFixedSize(FILE_CARD_WIDTH, FILE_CARD_HEIGHT)
        self.item_data = item_data
        self.file_path = item_data["path"]
        self.rotation_angle = item_data.get("rotation", 0)
        self.page_num = item_data.get("page", 0)
        self.is_encrypted = item_data.get("encrypted", False)
        self.click_to_toggle = click_to_toggle
        self.setObjectName("FileCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.number_label = QLabel(str(index), self)
        self.number_label.setObjectName("FileNumberBadge")
        self.number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.number_label.setFixedSize(CARD_NUMBER_LABEL_SIZE, CARD_NUMBER_LABEL_SIZE)
        self.number_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.number_label.show()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 35, 2, 5)
        self.layout.setSpacing(2)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label = QLabel()
        self.image_label.setObjectName("FilePreviewImage")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.image_label.setScaledContents(False)
        self.layout.addWidget(self.image_label)
        file_name = os.path.basename(self.file_path)
        display_name = truncate_filename(file_name)
        self.name_label = QLabel(display_name)
        self.name_label.setObjectName("FileNameLabel")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setFixedHeight(CARD_NAME_LABEL_HEIGHT)
        self.name_label.setToolTip(file_name)
        self.layout.addWidget(self.name_label)
        self.overlay_label = QLabel("", self)
        self.overlay_label.setObjectName("FileOverlay")
        self.overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overlay_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.overlay_label.hide()
        self.delete_button = QPushButton("X", self)
        self.delete_button.setObjectName("DeleteCardButton")
        self.delete_button.setFixedSize(
            CARD_ACTION_BUTTON_SIZE, CARD_ACTION_BUTTON_SIZE
        )
        self.delete_button.hide()
        self.delete_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_button.clicked.connect(self.on_delete_clicked)
        self.rotate_button = QPushButton("⟲", self)
        self.rotate_button.setObjectName("RotateCardButton")
        self.rotate_button.setFixedSize(
            CARD_ACTION_BUTTON_SIZE, CARD_ACTION_BUTTON_SIZE
        )
        self.rotate_button.hide()
        self.rotate_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rotate_button.clicked.connect(self.on_rotate_clicked)
        self.rotate_button.setToolTip("Rotate 90° Left")
        if self.click_to_toggle:
            self.delete_button.hide()
            self.rotate_button.hide()
            self.delete_button.setEnabled(False)
            self.rotate_button.setEnabled(False)
        self.update_visuals()

    def set_number(self, num):
        self.number_label.setText(str(num))

    def update_visuals(self):
        if self.is_encrypted:
            lock_pixmap = QPixmap("assets/ico/lock.png")
            if not lock_pixmap.isNull():
                self.image_label.setPixmap(lock_pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.image_label.setObjectName("EncryptedIconLabel")
            self.setToolTip("Password required")
            self.rotate_button.setEnabled(False)
        else:
            self.image_label.setStyleSheet("")
            self.setToolTip("")
            self.rotate_button.setEnabled(True)
            self.generate_thumbnail()

    def generate_thumbnail(self):
        if self.is_encrypted:
            return
        pixmap = get_pdf_thumbnail(self.file_path, self.page_num, self.rotation_angle)
        if pixmap:
            self.image_label.setPixmap(pixmap)
        else:
            fallback_pixmap = QPixmap("assets/ico/filesize.png")
            if not fallback_pixmap.isNull():
                self.image_label.setPixmap(fallback_pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def mousePressEvent(self, event):
        if self.click_to_toggle:
            self.delete_requested.emit(self.item_data)
            return
        if not self.overlay_label.isHidden():
            self.delete_requested.emit(self.item_data)
        else:
            super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay_label.setGeometry(0, 0, self.width(), self.height())
        center_x = self.width() // 2
        center_y = self.height() // 2
        self.delete_button.move(center_x + 5, center_y - 15)
        self.rotate_button.move(center_x - 35, center_y - 15)
        self.number_label.move(5, 5)

    def enterEvent(self, event):
        if not self.click_to_toggle:
            self.delete_button.show()
            if not self.is_encrypted:
                self.rotate_button.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.click_to_toggle:
            self.delete_button.hide()
            self.rotate_button.hide()
        super().leaveEvent(event)

    def on_delete_clicked(self):
        self.delete_requested.emit(self.item_data)

    def on_rotate_clicked(self):
        if self.is_encrypted:
            return
        self.rotation_angle = calculate_rotation(self.rotation_angle)
        self.generate_thumbnail()
        self.rotate_requested.emit(self.item_data)

    def update_content(self, item_data):
        self.item_data = item_data
        self.file_path = item_data["path"]
        self.rotation_angle = item_data.get("rotation", 0)
        self.page_num = item_data.get("page", 0)
        self.is_encrypted = item_data.get("encrypted", False)
        file_name = os.path.basename(self.file_path)
        display_name = truncate_filename(file_name)
        self.name_label.setText(display_name)
        self.name_label.setToolTip(file_name)
        self.update_visuals()
        self.set_placeholder(False)

    def set_placeholder(self, is_placeholder):
        self.setProperty("placeholder", is_placeholder)
        self.style().unpolish(self)
        self.style().polish(self)
        if is_placeholder:
            self.image_label.hide()
            self.name_label.hide()
            self.number_label.hide()
            self.delete_button.hide()
            self.rotate_button.hide()
        else:
            self.image_label.show()
            self.name_label.show()
            self.number_label.show()

    def mouseMoveEvent(self, e):
        if self.click_to_toggle:
            return
        if self.delete_button.underMouse() or self.rotate_button.underMouse():
            return
        if e.buttons() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.file_path)
            drag.setMimeData(mime)
            pixmap = QPixmap(self.size())
            self.set_placeholder(False)
            self.delete_button.hide()
            self.rotate_button.hide()
            self.render(pixmap)
            drag.setPixmap(pixmap)
            drag.exec(Qt.DropAction.MoveAction)

    def set_overlay(self, text, visible=True):
        self.overlay_label.setText(text)
        if visible:
            self.overlay_label.show()
            self.overlay_label.raise_()
        else:
            self.overlay_label.hide()
