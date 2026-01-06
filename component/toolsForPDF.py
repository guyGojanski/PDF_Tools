import os
import shutil
import platform
import subprocess
import fitz
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog


def get_downloads_folder():
    if os.name == "nt":
        return os.path.join(os.environ["USERPROFILE"], "Downloads")
    return os.path.join(os.path.expanduser("~"), "Downloads")


def open_file(path):
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.call(("open", path))
    else:
        subprocess.call(("xdg-open", path))


def validate_only_pdfs(file_list):
    for f in file_list:
        if not f.lower().endswith(".pdf"):
            return False, os.path.basename(f)
    return True, None


def calculate_rotation(current_angle):
    return (current_angle - 90) % 360


def get_pdf_thumbnail(file_path, page_num=0, rotation=0, width=150, height=145):
    try:
        doc = fitz.open(file_path)
        if page_num >= len(doc):
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
        print(f"Error generating thumbnail: {e}")
        return None


def apply_stylesheet(widget, filename="assets/style.qss"):
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
            except Exception:
                pass
    print(f"Warning: Stylesheet not found: {filename}")


def cleanup_temp_folder(folder_path):
    if os.path.exists(folder_path):
        try:
            shutil.rmtree(folder_path)
        except OSError:
            pass


def pick_pdf_files(parent):
    files, _ = QFileDialog.getOpenFileNames(
        parent, "Select PDF Files", "", "PDF Files (*.pdf)"
    )
    return files


def truncate_filename(filename, limit=20):
    if len(filename) > limit:
        return filename[: limit - 3] + "..."
    return filename


def safe_copy_file(src_path, target_folder):
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    filename = os.path.basename(src_path)
    dest_path = os.path.join(target_folder, filename)
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(dest_path):
        dest_path = os.path.join(target_folder, f"{base}_{counter}{ext}")
        counter += 1
    shutil.copy2(src_path, dest_path)
    return dest_path
