import os
import shutil
import platform
import subprocess
import logging
from contextlib import contextmanager
from typing import Optional, List
import fitz
from pypdf import PdfReader, PdfWriter
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QWidget, QPushButton
from assets.config import STYLESHEET

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


def is_valid_pdf(path: str) -> bool:
    try:
        if os.path.getsize(path) == 0:
            return False
        try:
            doc = fitz.open(path)
            if doc.is_encrypted:
                doc.close()
                return True
            if len(doc) == 0:
                doc.close()
                return False
            doc.close()
            return True
        except:
            return False
    except Exception:
        return False


def is_pdf_encrypted(path: str) -> bool:
    try:
        doc = fitz.open(path)
        encrypted = doc.is_encrypted
        doc.close()
        return encrypted
    except:
        return False


def attempt_pdf_decryption(
    src_path: str, password: str, temp_folder: str
) -> Optional[str]:
    try:
        reader = PdfReader(src_path)
        if reader.is_encrypted:
            result = reader.decrypt(password)
            if result == 0:
                return None
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        filename = os.path.basename(src_path)
        base, ext = os.path.splitext(filename)
        new_filename = f"decrypted_{base}{ext}"
        dest_path = os.path.join(temp_folder, new_filename)
        with open(dest_path, "wb") as f:
            writer.write(f)
        return dest_path
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return None


def calculate_rotation(current_angle: int) -> int:
    return (current_angle - 90) % 360


def get_pdf_thumbnail(
    file_path: str,
    page_num: int = 0,
    rotation: int = 0,
    width: int = 150,
    height: int = 145,
) -> Optional[QPixmap]:
    doc = None
    try:
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            return None
        if page_num >= len(doc):
            return None
        page = doc.load_page(page_num)
        page.set_rotation(rotation)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
        fmt = QImage.Format.Format_RGB888
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
        pixmap = QPixmap.fromImage(img)
        return pixmap.scaled(
            width,
            height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    except Exception:
        return None
    finally:
        if doc:
            doc.close()


def apply_stylesheet(widget: QWidget, filename: str = STYLESHEET) -> None:
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
                return
            except Exception as e:
                logger.warning(f"Failed to load stylesheet {path}: {e}")
                continue


def cleanup_temp_folder(folder_path: str) -> None:
    if os.path.exists(folder_path):
        try:
            shutil.rmtree(folder_path)
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
        return dest_path
    except PermissionError as e:
        raise OSError(f"Permission denied: {e}")
    except OSError as e:
        raise OSError(f"Disk full or IO error: {e}")


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
    back_to_dashboard = pyqtSignal()

    def __init__(self, temp_folder: str, header_title: str):
        super().__init__()
        self.temp_folder = temp_folder
        self.header_title = header_title
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        apply_stylesheet(self, STYLESHEET)

    def go_back(self) -> None:
        cleanup_temp_folder(self.temp_folder)
        self.back_to_dashboard.emit()


def get_parity_indices(total_pages: int, parity: str) -> List[int]:
    if parity == "odd":
        return list(range(0, total_pages, 2))
    elif parity == "even":
        return list(range(1, total_pages, 2))
    return []
