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
)
from PyQt6.QtCore import Qt
from pypdf import PdfWriter, PdfReader

from component.pdf_grid import PDFGrid
from component.header_bar import HeaderBar
from component.toolsForPDF import (
    get_downloads_folder,
    open_file,
    cleanup_temp_folder,
    button_operation,
    BaseToolWindow,
    get_unique_filename,
    get_parity_indices,
)
from assets.config import (
    DELETE_MAX_FILES,
    EDITED_OUTPUT_PREFIX,
)


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
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 20)

        self.header = HeaderBar(self.header_title)
        self.header.back_clicked.connect(self.go_back)
        layout.addWidget(self.header)

        input_container = QVBoxLayout()
        input_container.setContentsMargins(50, 0, 50, 0)
        input_container.setSpacing(5)

        info_row = QHBoxLayout()
        self.total_pages_label = QLabel(f"Total pages: {self.total_pages}")
        self.total_pages_label.setObjectName("TotalPagesLabel")
        info_row.addWidget(self.total_pages_label)

        self.pages_to_remove_label = QLabel("Select pages to remove:")
        self.pages_to_remove_label.setObjectName("RemoveLabel")
        self.pages_to_remove_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        info_row.addWidget(self.pages_to_remove_label)
        input_container.addLayout(info_row)

        input_row_layout = QHBoxLayout()
        input_row_layout.setSpacing(10)

        self.pages_input = QLineEdit()
        self.pages_input.setObjectName("PagesInput")
        self.pages_input.setPlaceholderText("e.g. 1-3, 5")
        self.pages_input.setFixedSize(600, 45)
        self.pages_input.textChanged.connect(self.clean_and_update)
        input_row_layout.addWidget(self.pages_input)

        self.btn_odd = QPushButton("Odd")
        self.btn_odd.setObjectName("ParityButton")
        self.btn_odd.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_odd.setToolTip("Select all Odd pages (1, 3, 5...)")
        self.btn_odd.setFixedSize(50, 50)
        self.btn_odd.clicked.connect(lambda: self.toggle_parity("odd"))
        input_row_layout.addWidget(self.btn_odd)

        self.btn_even = QPushButton("Even")
        self.btn_even.setObjectName("ParityButton")
        self.btn_even.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_even.setToolTip("Select all Even pages (2, 4, 6...)")
        self.btn_even.setFixedSize(50, 50)
        self.btn_even.clicked.connect(lambda: self.toggle_parity("even"))
        input_row_layout.addWidget(self.btn_even)

        input_row_layout.addStretch()

        input_container.addLayout(input_row_layout)

        layout.addLayout(input_container)

        self.pdf_grid = PDFGrid(
            self.pages_data,
            max_items=DELETE_MAX_FILES,
            on_delete_callback=self.toggle_mark,
        )
        layout.addWidget(self.pdf_grid)

        self.save_btn = QPushButton("Save Changes (Remove Marked Pages)")
        self.save_btn.setObjectName("MergeButton")
        self.save_btn.setMinimumHeight(60)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(50, 0, 50, 0)
        btn_layout.addWidget(self.save_btn)
        self.save_btn.clicked.connect(self.perform_save)
        layout.addLayout(btn_layout)

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

    def clean_and_update(self):
        text = self.pages_input.text()
        cleaned_text = re.sub(r"[^0-9,\-]", "", text)
        if text != cleaned_text:
            pos = self.pages_input.cursorPosition()
            self.pages_input.setText(cleaned_text)
            self.pages_input.setCursorPosition(max(0, pos - 1))
        self.live_update_marks(cleaned_text.replace(" ", ""))

    def live_update_marks(self, text):
        if not text:
            self.clear_all_marks()
            return
        pages_to_mark = set()
        parts = text.split(",")
        try:
            for part in parts:
                if not part:
                    continue
                if "-" in part:
                    if part.endswith("-") or part.startswith("-"):
                        continue
                    start_str, end_str = part.split("-")
                    start, end = int(start_str), int(end_str)
                    if 1 <= start < end <= self.total_pages:
                        for p in range(start, end + 1):
                            pages_to_mark.add(p)
                else:
                    p = int(part)
                    if 1 <= p <= self.total_pages:
                        pages_to_mark.add(p)
            for item in self.pages_data:
                should_be_marked = (item["page"] + 1) in pages_to_mark
                if item["marked"] != should_be_marked:
                    item["marked"] = should_be_marked
                    card = self.pdf_grid.get_card_by_data(item)
                    if card:
                        card.set_overlay("X", visible=should_be_marked)
        except Exception:
            pass

    def clear_all_marks(self):
        for item in self.pages_data:
            if item["marked"]:
                item["marked"] = False
                card = self.pdf_grid.get_card_by_data(item)
                if card:
                    card.set_overlay("", visible=False)

    def toggle_mark(self, item_data):
        item_data["marked"] = not item_data.get("marked", False)
        card = self.pdf_grid.get_card_by_data(item_data)
        if card:
            card.set_overlay("X", visible=item_data["marked"])

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
                for item in items:
                    if item.get("marked"):
                        continue
                    page = reader.pages[item["page"]]
                    if item["rotation"] != 0:
                        page.rotate(item["rotation"])
                    writer.add_page(page)
                output_name = (
                    f"{EDITED_OUTPUT_PREFIX}{os.path.basename(self.file_path)}"
                )
                output_path = get_unique_filename(get_downloads_folder(), output_name)
                with open(output_path, "wb") as f:
                    writer.write(f)
                QMessageBox.information(self, "Success", f"File saved successfully!")
                open_file(output_path)
                self.go_back()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Save failed: {str(e)}")
            finally:
                cleanup_temp_folder(self.temp_folder)
