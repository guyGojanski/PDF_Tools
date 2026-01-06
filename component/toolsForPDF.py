import os
import shutil
import platform
import subprocess
import logging
from contextlib import contextmanager
from typing import Optional, Tuple, List, Any
import fitz
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QWidget, QPushButton, QMessageBox

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def get_downloads_folder() -> str:
    if os.name == "nt":
        return os.path.join(os.environ["USERPROFILE"], "Downloads")
    return os.path.join(os.path.expanduser("~"), "Downloads")


def open_file(path: str) -> None:
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.call(("open", path))
        else:
            subprocess.call(("xdg-open", path))
    except Exception as e:
        logger.error(f"Failed to open file {path}: {e}")


def validate_only_pdfs(file_list: List[str]) -> Tuple[bool, Optional[str]]:
    for f in file_list:
        if not f.lower().endswith(".pdf"):
            return False, os.path.basename(f)
    return True, None


def calculate_rotation(current_angle: int) -> int:
    return (current_angle - 90) % 360


def get_pdf_thumbnail(
    file_path: str,
    page_num: int = 0,
    rotation: int = 0,
    width: int = 150,
    height: int = 145,
) -> Optional[QPixmap]:
    try:
        doc = fitz.open(file_path)
        if page_num >= len(doc):
            doc.close()
            return None
        page = doc.load_page(page_num)
        page.set_rotation(rotation)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
        fmt = QImage.Format.Format_RGB888
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
        pixmap = QPixmap.fromImage(img)
        doc.close()
        return pixmap.scaled(
            width,
            height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    except Exception as e:
        logger.error(f"Error generating thumbnail for {file_path}: {e}")
        return None


def apply_stylesheet(widget: QWidget, filename: str = "assets/style.qss") -> None:
    possible_paths = [
        filename,
        os.path.join("..", filename),
        os.path.join(os.path.dirname(__file__), "..", filename),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    widget.setStyleSheet(widget.styleSheet() + f.read())
                logger.info(f"Stylesheet loaded: {path}")
                return
            except Exception as e:
                logger.warning(f"Failed to load stylesheet {path}: {e}")
                continue
    error_msg = f"Stylesheet not found: {filename}"
    logger.error(error_msg)
    QMessageBox.warning(widget, "Stylesheet Error", error_msg)


def cleanup_temp_folder(folder_path: str) -> None:
    if os.path.exists(folder_path):
        try:
            shutil.rmtree(folder_path)
            logger.info(f"Cleaned up temp folder: {folder_path}")
        except OSError as e:
            logger.warning(f"Failed to cleanup {folder_path}: {e}")


def pick_pdf_files(parent: QWidget) -> List[str]:
    files, _ = QFileDialog.getOpenFileNames(
        parent, "Select PDF Files", "", "PDF Files (*.pdf)"
    )
    return files


def truncate_filename(filename: str, limit: int = 20) -> str:
    if len(filename) > limit:
        return filename[: limit - 3] + "..."
    return filename


def safe_copy_file(src_path: str, target_folder: str) -> str:
    try:
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)
            logger.info(f"Created target folder: {target_folder}")
        filename = os.path.basename(src_path)
        dest_path = os.path.join(target_folder, filename)
        base, ext = os.path.splitext(filename)

        if os.path.exists(dest_path):
            counter = 1
            while True:
                candidate = os.path.join(target_folder, f"{base}({counter}){ext}")
                if not os.path.exists(candidate):
                    dest_path = candidate
                    break
                counter += 1

        shutil.copy2(src_path, dest_path)
        logger.info(f"Copied file: {src_path} -> {dest_path}")
        return dest_path
    except PermissionError as e:
        logger.error(f"Permission denied copying {src_path}: {e}")
        raise OSError(f"Permission denied: {e}")
    except OSError as e:
        if "space" in str(e).lower():
            logger.error(f"Disk full copying {src_path}: {e}")
            raise OSError(f"Disk full: {e}")
        logger.error(f"Failed to copy {src_path}: {e}")
        raise


@contextmanager
def button_operation(button: QPushButton, loading_text: str, original_text: str):
    button.setText(loading_text)
    button.setEnabled(False)
    try:
        yield
    finally:
        button.setText(original_text)
        button.setEnabled(True)


def get_unique_filename(folder: str, filename: str) -> str:
    """Generate a unique filename by appending (counter) if file exists."""
    dest_path = os.path.join(folder, filename)
    if not os.path.exists(dest_path):
        return dest_path

    base, ext = os.path.splitext(filename)
    counter = 1
    while True:
        candidate = os.path.join(folder, f"{base}({counter}){ext}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1


class BaseToolWindow(QWidget):
    """Base class for PDF tool windows with common initialization and navigation."""

    back_to_dashboard = pyqtSignal()

    def __init__(self, temp_folder: str, header_title: str):
        super().__init__()
        self.temp_folder = temp_folder
        self.header_title = header_title
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        apply_stylesheet(self, "assets/style.qss")

    def go_back(self) -> None:
        """Navigate back to dashboard and cleanup temporary folder."""
        cleanup_temp_folder(self.temp_folder)
        self.back_to_dashboard.emit()
