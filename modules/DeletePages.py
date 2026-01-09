import os
import fitz
import re
from PyQt6.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QLineEdit,
    QApplication,
    QWidget,
    QSizePolicy,
)
from PyQt6.QtCore import Qt
from pypdf import PdfWriter, PdfReader
from component.pdf_grid import PDFGrid
from component.header_bar import HeaderBar
from component.toolsForPDF import *
from assets.config import *


class DeletePagesWindow(BaseToolWindow):
    def __init__(self, file_path, temp_folder):
        doc = fitz.open(file_path)
        total_pages = len(doc)
        doc.close()
        super().__init__(temp_folder, f"Editing: {os.path.basename(file_path)}")
        self.file_path = file_path
        self.total_pages = total_pages
        self.pages_data = [
            {"path": file_path, "page": i, "rotation": 0, "marked": False}
            for i in range(self.total_pages)
        ]
        self._suppress_text_update = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 20)
        self.header = HeaderBar(self.header_title)
        self.header.back_clicked.connect(self.go_back)
        layout.addWidget(self.header)
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(20, 0, 20, 0)
        center_layout.setSpacing(12)
        self.pdf_grid = PDFGrid(
            self.pages_data,
            max_items=MAX_DELETE_FILES,
            on_delete_callback=self.toggle_mark,
            click_to_toggle=True,
            drag_enabled=False,
        )
        center_layout.addWidget(self.pdf_grid)
        content_layout.addWidget(center_container, stretch=1)
        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(SIDEBAR_WIDTH)
        self.sidebar.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setSpacing(14)
        sidebar_layout.setContentsMargins(22, 18, 22, 18)
        sidebar_layout.addWidget(QLabel("Delete Pages", objectName="SidebarTitle"))
        self.total_pages_label = QLabel(f"Total pages: {self.total_pages}")
        self.total_pages_label.setObjectName("SidebarStatLabel")
        sidebar_layout.addWidget(self.total_pages_label)
        self.pages_to_remove_label = QLabel("Select pages to remove:")
        self.pages_to_remove_label.setObjectName("RemoveLabel")
        self.pages_to_remove_label.setWordWrap(True)
        sidebar_layout.addWidget(self.pages_to_remove_label)
        self.pages_input = QLineEdit()
        self.pages_input.setObjectName("PagesInput")
        self.pages_input.setPlaceholderText("e.g. 1-4, 7")
        self.pages_input.setMinimumHeight(PAGES_INPUT_HEIGHT)
        self.pages_input.textChanged.connect(self.clean_and_update)
        sidebar_layout.addWidget(self.pages_input)
        parity_row = QHBoxLayout()
        parity_row.setSpacing(10)
        self.btn_odd = QPushButton("Odd")
        self.btn_odd.setObjectName("ParityButton")
        self.btn_odd.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_odd.setToolTip("Select all Odd pages (1, 3, 5...)")
        self.btn_odd.setMinimumHeight(PARITY_BUTTON_HEIGHT)
        self.btn_odd.setMinimumWidth(PARITY_BUTTON_WIDTH)
        self.btn_odd.clicked.connect(lambda: self.toggle_parity("odd"))
        parity_row.addWidget(self.btn_odd)
        self.btn_even = QPushButton("Even")
        self.btn_even.setObjectName("ParityButton")
        self.btn_even.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_even.setToolTip("Select all Even pages (2, 4, 6...)")
        self.btn_even.setMinimumHeight(PARITY_BUTTON_HEIGHT)
        self.btn_even.setMinimumWidth(PARITY_BUTTON_WIDTH)
        self.btn_even.clicked.connect(lambda: self.toggle_parity("even"))
        parity_row.addWidget(self.btn_even)
        parity_row.addStretch()
        sidebar_layout.addLayout(parity_row)
        hint_label = QLabel("Tip: Click cards to mark them, or type ranges like 1-4,7")
        hint_label.setObjectName("SidebarHint")
        hint_label.setWordWrap(True)
        sidebar_layout.addWidget(hint_label)
        sidebar_layout.addStretch()
        self.save_btn = QPushButton("Save Changes (Remove Marked Pages)")
        self.save_btn.setObjectName("MergeButton")
        self.save_btn.setMinimumHeight(PRIMARY_BUTTON_HEIGHT)
        self.save_btn.clicked.connect(self.perform_save)
        sidebar_layout.addWidget(self.save_btn)
        content_layout.addWidget(self.sidebar, stretch=0)
        layout.addLayout(content_layout)

    def toggle_parity(self, parity):
        indices = get_parity_indices(self.total_pages, parity)
        all_marked = True
        for i in indices:
            if not self.pages_data[i]["marked"]:
                all_marked = False
                break
        new_state = not all_marked
        for i in indices:
            item = self.pages_data[i]
            if item["marked"] != new_state:
                item["marked"] = new_state
                card = self.pdf_grid.get_card_by_data(item)
                if card:
                    card.set_overlay("X", visible=new_state)
        self._update_input_from_marks()

    def clean_and_update(self):
        if self._suppress_text_update:
            return
        text = self.pages_input.text()
        cleaned_text = re.sub(r"[^0-9,\-]", "", text)
        if text != cleaned_text:
            pos = self.pages_input.cursorPosition()
            self.pages_input.setText(cleaned_text)
            self.pages_input.setCursorPosition(max(0, pos - 1))
        self.live_update_marks(cleaned_text.replace(" ", ""))

    def live_update_marks(self, text):
        if self._suppress_text_update:
            return
        if not text:
            self.clear_all_marks()
            return
        pages_to_mark = set(parse_page_ranges(text, self.total_pages))
        for item in self.pages_data:
            should_be_marked = item["page"] in pages_to_mark
            if item["marked"] != should_be_marked:
                item["marked"] = should_be_marked
                card = self.pdf_grid.get_card_by_data(item)
                if card:
                    card.set_overlay("X", visible=should_be_marked)

    def clear_all_marks(self):
        for item in self.pages_data:
            if item["marked"]:
                item["marked"] = False
                card = self.pdf_grid.get_card_by_data(item)
                if card:
                    card.set_overlay("", visible=False)
        self._update_input_from_marks()

    def toggle_mark(self, item_data):
        item_data["marked"] = not item_data.get("marked", False)
        card = self.pdf_grid.get_card_by_data(item_data)
        if card:
            card.set_overlay("X", visible=item_data["marked"])
        self._update_input_from_marks()

    def _update_input_from_marks(self):
        marked_pages = sorted(
            [idx + 1 for idx, item in enumerate(self.pages_data) if item.get("marked")]
        )
        text = format_pages_as_ranges(marked_pages)
        self._suppress_text_update = True
        self.pages_input.setText(text)
        self._suppress_text_update = False

    def perform_save(self):
        items = self.pdf_grid.get_items()
        pages_to_keep = [item for item in items if not item.get("marked", False)]
        if not pages_to_keep:
            QMessageBox.warning(self, "Error", "Cannot delete all pages!")
            return
        with button_operation(self.save_btn, "Saving...", "Save Changes"):
            QApplication.processEvents()
            try:
                writer = PdfWriter()
                reader = PdfReader(self.file_path)
                pages_indices = [
                    item["page"] for item in items if not item.get("marked")
                ]
                rotations = {item["page"]: item["rotation"] for item in items}
                write_pdf_with_rotation(writer, reader, pages_indices, rotations)
                output_name = (
                    f"{EDITED_OUTPUT_PREFIX}{os.path.basename(self.file_path)}"
                )
                if save_pdf_with_success(writer, output_name, self):
                    self.go_back()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Save failed: {str(e)}")
            finally:
                cleanup_temp_folder(self.temp_folder)
