import sys
import os
from PyQt6.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
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
    pick_pdf_files,
    safe_copy_file,
    button_operation,
    BaseToolWindow,
    get_unique_filename,
)

MAX_FILES = 5


class MergePreviewWindow(BaseToolWindow):
    def __init__(self, file_list_paths, temp_folder, max_files=MAX_FILES):
        super().__init__(temp_folder, "Merge PDF Documents")
        initial_items = [{"path": f, "rotation": 0, "page": 0} for f in file_list_paths]
        self.max_files = max_files
        self._init_ui(initial_items)

    def _init_ui(self, initial_items):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(0, 0, 0, 20)

        self.header = HeaderBar(self.header_title)
        self.header.back_clicked.connect(self.go_back)
        main_layout.addWidget(self.header)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(20, 0, 20, 0)

        self.title_label = QLabel()
        self.title_label.setObjectName("MergeTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.add_btn = QPushButton("+")
        self.add_btn.setObjectName("AddButton")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setFixedSize(40, 40)
        self.add_btn.clicked.connect(self.on_add_clicked)

        header_layout.addStretch()
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.add_btn)
        main_layout.addLayout(header_layout)

        self.pdf_grid = PDFGrid(initial_items, max_items=self.max_files)
        self.pdf_grid.items_changed.connect(self.update_title)
        main_layout.addWidget(self.pdf_grid)

        self.merge_btn = QPushButton("Merge PDF Now")
        self.merge_btn.setObjectName("MergeButton")
        self.merge_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.merge_btn.setMinimumHeight(60)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(50, 0, 50, 0)
        btn_layout.addWidget(self.merge_btn)
        self.merge_btn.clicked.connect(self.perform_merge)
        main_layout.addLayout(btn_layout)

        self.update_title()

    def update_title(self):
        count = len(self.pdf_grid.get_items())
        self.title_label.setText(f"Selected {count} / {self.max_files} Files")

    def on_add_clicked(self):
        current_count = len(self.pdf_grid.get_items())
        if current_count >= self.max_files:
            QMessageBox.warning(self, "Limit Reached", "Maximum files reached.")
            return
        files = pick_pdf_files(self)
        if not files:
            return
        slots_left = self.max_files - current_count
        for f in files[:slots_left]:
            try:
                dest_path = safe_copy_file(f, self.temp_folder)
                self.pdf_grid.add_item({"path": dest_path, "rotation": 0, "page": 0})
            except OSError as e:
                QMessageBox.critical(self, "Copy Error", str(e))
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to add file: {str(e)}")

    def perform_merge(self):
        items = self.pdf_grid.get_items()
        if not items:
            QMessageBox.warning(self, "No Files", "Please add files.")
            return

        with button_operation(self.merge_btn, "Merging...", "Merge PDF Now"):
            QApplication.processEvents()
            try:
                writer = PdfWriter()
                for item in items:
                    reader = PdfReader(item["path"])
                    for page in reader.pages:
                        if item["rotation"] != 0:
                            page.rotate(item["rotation"])
                        writer.add_page(page)
                output_path = get_unique_filename(
                    get_downloads_folder(), "merged_result.pdf"
                )
                with open(output_path, "wb") as f:
                    writer.write(f)
                QMessageBox.information(self, "Success", f"Saved at: {output_path}")
                open_file(output_path)
                self.go_back()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
            finally:
                cleanup_temp_folder(self.temp_folder)
