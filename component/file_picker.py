import sys
import os
import logging
from typing import List
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QMessageBox,
    QDialog,
    QProgressDialog,
)
from PyQt6.QtCore import Qt
from component.toolsForPDF import (
    get_downloads_folder,
    apply_stylesheet,
    safe_copy_file,
    is_valid_pdf,
)
from assets.config import FILE_PICKER_DEFAULT_FOLDER, STYLESHEET

logger = logging.getLogger(__name__)


class FileSelector(QDialog):
    def __init__(self, max_files: int, target_folder: str = "temp_files"):
        super().__init__()
        self.max_files = max_files
        self.target_folder = target_folder
        self.selected_files: List[str] = []
        self.setObjectName("MainWindow")
        apply_stylesheet(self, STYLESHEET)
        self.setWindowTitle("File Selector")
        self.setFixedSize(400, 220)
        self.setAcceptDrops(True)
        self._init_ui()

    def _init_ui(self) -> None:
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

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.overlay.show()

    def dragLeaveEvent(self, event) -> None:
        self.overlay.hide()

    def dropEvent(self, event) -> None:
        self.overlay.hide()
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        self.process_files(files)

    def open_files(self) -> None:
        initial_dir = get_downloads_folder()
        if self.max_files == 1:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Single File", initial_dir, "PDF Files (*.pdf)"
            )
            if file_path:
                self.process_files([file_path])
        else:
            files, _ = QFileDialog.getOpenFileNames(
                self,
                f"Select up to {self.max_files} Files",
                initial_dir,
                "PDF Files (*.pdf)",
            )
            if files:
                self.process_files(files)

    def process_files(self, files: List[str]) -> None:
        if len(files) > self.max_files:
            QMessageBox.warning(
                self, "Limit Exceeded", f"Max allowed: {self.max_files} files."
            )
            return
        progress = QProgressDialog(
            "Copying and validating files...", "Cancel", 0, len(files), self
        )
        progress.setWindowTitle("Please Wait")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        copied_paths = []
        errors = []
        skipped_files = []
        for i, src_path in enumerate(files):
            if progress.wasCanceled():
                break
            progress.setValue(i)
            progress.setLabelText(f"Processing: {os.path.basename(src_path)}")
            QApplication.processEvents()
            if not src_path.lower().endswith(".pdf"):
                continue
            if not is_valid_pdf(src_path):
                skipped_files.append(os.path.basename(src_path))
                continue
            try:
                dest_path = safe_copy_file(src_path, self.target_folder)
                copied_paths.append(os.path.abspath(dest_path))
            except OSError as e:
                errors.append(f"{os.path.basename(src_path)}: {str(e)}")
            except Exception as e:
                logger.error(f"Failed to copy {src_path}: {e}")
                errors.append(f"{os.path.basename(src_path)}: Unexpected error")
        progress.setValue(len(files))

        if errors:
            QMessageBox.warning(
                self, "Copy Errors", "Failed to copy:\n" + "\n".join(errors)
            )
        if skipped_files:
            msg = "The following files were skipped because they are empty or invalid:\n\n"
            msg += "\n".join(skipped_files[:10])
            if len(skipped_files) > 10:
                msg += f"\n...and {len(skipped_files) - 10} more."
            QMessageBox.warning(self, "Invalid Files Skipped", msg)
        self.selected_files = copied_paths
        self.accept()


def get_files(
    max_files: int, target_folder: str = FILE_PICKER_DEFAULT_FOLDER
) -> List[str]:
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    window = FileSelector(max_files, target_folder)
    window.exec()
    return window.selected_files
