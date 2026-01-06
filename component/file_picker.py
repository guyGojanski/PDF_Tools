import sys
import os
import shutil
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QMessageBox,
    QDialog,  # שינוי 1: ייבוא QDialog
)
from PyQt6.QtCore import Qt
from component.toolsForPDF import get_downloads_folder


class FileSelector(QDialog):  # שינוי 2: ירושה מ-QDialog במקום QWidget
    def __init__(self, max_files: int, target_folder: str = "temp_files"):
        super().__init__()
        self.max_files = max_files
        self.target_folder = target_folder
        self.selected_files = []
        self.setObjectName("MainWindow")  # שומרים על השם לעיצוב, למרות שזה דיאלוג
        self._load_stylesheet()
        self.setWindowTitle("File Selector")
        self.setFixedSize(400, 220)
        self.setAcceptDrops(True)
        self._init_ui()

    def _load_stylesheet(self, filename: str = "assets/style.qss"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        style_path = os.path.abspath(os.path.join(base_dir, "..", filename))
        if os.path.exists(style_path):
            try:
                with open(style_path, "r") as f:
                    self.setStyleSheet(f.read())
            except Exception as e:
                print(f"Error loading style: {e}")
        else:
            print(f"Style file not found: {style_path}")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.label = QLabel(f"Drag up to {self.max_files} files here\n(Local Copy)")
        self.label.setObjectName("InstructionLabel")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        self.button = QPushButton("Select Files")
        self.button.setObjectName("SelectButton")
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.clicked.connect(self.open_files)
        layout.addWidget(self.button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.overlay = QLabel("Drop Here!", self)
        self.overlay.setObjectName("Overlay")
        self.overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overlay.resize(self.size())
        self.overlay.hide()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.overlay.show()

    def dragLeaveEvent(self, event):
        self.overlay.hide()

    def dropEvent(self, event):
        self.overlay.hide()
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        self.process_files(files)

    def open_files(self):
        initial_dir = get_downloads_folder()
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", initial_dir, "PDF Files (*.pdf)"
        )
        if files:
            self.process_files(files)

    def process_files(self, files: list):
        if len(files) > self.max_files:
            QMessageBox.warning(
                self, "Limit Exceeded", f"Max allowed: {self.max_files} files."
            )
            return
        if not os.path.exists(self.target_folder):
            try:
                os.makedirs(self.target_folder)
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Cannot create folder: {e}")
                return
        copied_paths = []
        for src_path in files:
            if not src_path.lower().endswith(".pdf"):  # בדיקה נוספת לוודא שזה PDF
                continue
            filename = os.path.basename(src_path)
            dest_path = os.path.join(self.target_folder, filename)
            try:
                shutil.copy2(src_path, dest_path)
                copied_paths.append(os.path.abspath(dest_path))
            except Exception as e:
                print(f"Failed to copy {filename}: {e}")
        self.selected_files = copied_paths
        self.accept()  # שינוי 3: סוגר את הדיאלוג בהצלחה (במקום self.close)


def get_files(max_files: int, target_folder: str = "temp_uploads") -> list:
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    window = FileSelector(max_files, target_folder)
    window.exec()
    return window.selected_files
