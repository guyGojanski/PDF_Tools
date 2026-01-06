import sys
import os
import shutil
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from pypdf import PdfWriter, PdfReader
from component.pdf_grid import PDFGrid
from component.toolsForPDF import (
    get_downloads_folder,
    open_file,
    apply_stylesheet,
    cleanup_temp_folder,
    pick_pdf_files,
)
from component.file_picker import get_files
from component.header_bar import HeaderBar

MAX_FILES = 5

class MergePreviewWindow(QWidget):
    def __init__(self, file_list_paths, temp_folder, max_files=MAX_FILES):
        super().__init__()
        initial_items = [{"path": f, "rotation": 0, "page": 0} for f in file_list_paths]
        self.temp_folder = temp_folder
        self.max_files = max_files
        self.setWindowTitle("Review Files Before Merge")
        self.setObjectName("MergePreviewWindow")
        self.setMinimumSize(900, 600)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        apply_stylesheet(self, "style.qss")
        self._init_ui(initial_items)

    def _init_ui(self, initial_items):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(0, 0, 0, 20)

        self.header = HeaderBar("Merge PDF Documents")
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

    def go_back(self):
        cleanup_temp_folder(self.temp_folder)
        from PDF import PDFDashboard
        self.main_menu = PDFDashboard()
        self.main_menu.show()
        self.close()

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
        files_to_add = files[:slots_left]
        count_added = 0
        for f in files_to_add:
            filename = os.path.basename(f)
            dest_path = os.path.join(self.temp_folder, filename)
            try:
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(filename)
                    c = 1
                    while os.path.exists(os.path.join(self.temp_folder, f"{base}_{c}{ext}")):
                        c += 1
                    dest_path = os.path.join(self.temp_folder, f"{base}_{c}{ext}")
                shutil.copy2(f, dest_path)
                self.pdf_grid.add_item({"path": dest_path, "rotation": 0, "page": 0})
                count_added += 1
            except Exception:
                pass
        if count_added > 0:
            QMessageBox.information(self, "Added", f"{count_added} files added.")

    def perform_merge(self):
        items = self.pdf_grid.get_items()
        if not items:
            QMessageBox.warning(self, "No Files", "Please add files.")
            return
        self.merge_btn.setText("Merging...")
        self.merge_btn.setEnabled(False)
        QApplication.processEvents()
        try:
            writer = PdfWriter()
            for item in items:
                reader = PdfReader(item["path"])
                for page in reader.pages:
                    if item["rotation"] != 0:
                        page.rotate(item["rotation"])
                    writer.add_page(page)
            output_path = os.path.join(get_downloads_folder(), "merged_result.pdf")
            with open(output_path, "wb") as f:
                writer.write(f)
            QMessageBox.information(self, "Success", f"Saved at: {output_path}")
            open_file(output_path)
            self.go_back()
        except Exception as e:
            self.merge_btn.setText("Merge PDF Now")
            self.merge_btn.setEnabled(True)
            QMessageBox.critical(self, "Error", str(e))
        finally:
            cleanup_temp_folder(self.temp_folder)

def main():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    TEMP_FOLDER = "merge_temp_files"
    files = get_files(max_files=MAX_FILES, target_folder=TEMP_FOLDER)
    if not files:
        cleanup_temp_folder(TEMP_FOLDER)
        sys.exit()
    for f in files:
        if not f.lower().endswith(".pdf"):
            QMessageBox.critical(None, "Error", "Only PDF files allowed")
            cleanup_temp_folder(TEMP_FOLDER)
            sys.exit()
    window = MergePreviewWindow(files, TEMP_FOLDER, max_files=MAX_FILES)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()