import os
from PyQt6.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QApplication,
    QProgressDialog,
    QDialog,
    QLineEdit,
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
    is_valid_pdf,
    is_pdf_encrypted,
    attempt_pdf_decryption,
)
from assets.config import (
    MERGE_MAX_FILES,
    MERGE_HEADER_TITLE,
    MERGED_OUTPUT_NAME,
)


class PasswordInputDialog(QDialog):
    def __init__(self, filename, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Password Required")
        self.setObjectName("PasswordDialog")
        self.setFixedSize(450, 300)
        self.password = None
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        title = QLabel("File requires password")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)
        file_label = QLabel(f"File: {filename}")
        file_label.setObjectName("FileLabel")
        file_label.setWordWrap(True)
        layout.addWidget(file_label)
        input_container = QHBoxLayout()
        input_container.setSpacing(5)
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter Password")
        self.input_field.setEchoMode(QLineEdit.EchoMode.Password)
        input_container.addWidget(self.input_field)
        self.eye_btn = QPushButton("👁️")
        self.eye_btn.setObjectName("EyeButton")
        self.eye_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.eye_btn.clicked.connect(self.toggle_visibility)
        input_container.addWidget(self.eye_btn)
        layout.addLayout(input_container)
        self.send_btn = QPushButton("Unlock & Add")
        self.send_btn.setObjectName("SendButton")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self.verify)
        layout.addWidget(self.send_btn)

    def toggle_visibility(self):
        if self.input_field.echoMode() == QLineEdit.EchoMode.Password:
            self.input_field.setEchoMode(QLineEdit.EchoMode.Normal)
            self.eye_btn.setText("🔒")
        else:
            self.input_field.setEchoMode(QLineEdit.EchoMode.Password)
            self.eye_btn.setText("👁️")

    def verify(self):
        pwd = self.input_field.text().strip()
        if pwd:
            self.password = pwd
            self.accept()


class MergePreviewWindow(BaseToolWindow):
    def __init__(self, file_list_paths, temp_folder, max_files=MERGE_MAX_FILES):
        super().__init__(temp_folder, MERGE_HEADER_TITLE)
        initial_items = []
        for f in file_list_paths:
            encrypted = is_pdf_encrypted(f)
            initial_items.append(
                {"path": f, "rotation": 0, "page": 0, "encrypted": encrypted}
            )

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
        files_to_process = files[:slots_left]
        if not files_to_process:
            return
        progress = QProgressDialog(
            "Processing files...", "Cancel", 0, len(files_to_process), self
        )
        progress.setWindowTitle("Please Wait")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        items_to_add = []
        skipped_files = []
        for i, f in enumerate(files_to_process):
            if progress.wasCanceled():
                break
            progress.setValue(i)
            progress.setLabelText(f"Loading: {os.path.basename(f)}")
            QApplication.processEvents()
            try:
                if not is_valid_pdf(f):
                    skipped_files.append(os.path.basename(f))
                    continue
                dest_path = safe_copy_file(f, self.temp_folder)
                encrypted = is_pdf_encrypted(dest_path)
                items_to_add.append(
                    {
                        "path": dest_path,
                        "rotation": 0,
                        "page": 0,
                        "encrypted": encrypted,
                    }
                )
            except Exception as e:
                print(f"Error preparing file {f}: {e}")
        progress.setValue(len(files_to_process))
        if skipped_files:
            msg = "The following files were skipped because they are empty or invalid:\n\n"
            msg += "\n".join(skipped_files[:10])
            if len(skipped_files) > 10:
                msg += f"\n...and {len(skipped_files) - 10} more."
            QMessageBox.warning(self, "Invalid Files Skipped", msg)
        if items_to_add:
            self.pdf_grid.add_items_batch(items_to_add)

    def perform_merge(self):
        items = self.pdf_grid.get_items()
        if not items:
            QMessageBox.warning(self, "No Files", "Please add files.")
            return
        files_to_merge = []

        for item in items:
            final_path = item["path"]
            if item.get("encrypted"):
                decryption_success = False
                while True:
                    dialog = PasswordInputDialog(os.path.basename(final_path), self)
                    result = dialog.exec()
                    if result == QDialog.DialogCode.Accepted:
                        password = dialog.password
                        decrypted_path = attempt_pdf_decryption(
                            final_path, password, self.temp_folder
                        )
                        if decrypted_path:
                            final_path = decrypted_path
                            decryption_success = True
                            break
                        else:
                            retry = QMessageBox.warning(
                                self,
                                "Incorrect Password",
                                f"Failed to unlock:\n{os.path.basename(final_path)}\n\nTry again?",
                                QMessageBox.StandardButton.Yes
                                | QMessageBox.StandardButton.No,
                            )
                            if retry == QMessageBox.StandardButton.No:
                                break
                    else:
                        break
                if decryption_success:
                    files_to_merge.append(
                        {"path": final_path, "rotation": item["rotation"]}
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Skipped File",
                        f"Skipping encrypted file:\n{os.path.basename(final_path)}",
                    )
            else:
                files_to_merge.append(
                    {"path": final_path, "rotation": item["rotation"]}
                )
        if not files_to_merge:
            QMessageBox.warning(self, "Aborted", "No valid files left to merge.")
            return
        with button_operation(self.merge_btn, "Merging...", "Merge PDF Now"):
            QApplication.processEvents()
            try:
                writer = PdfWriter()
                for item in files_to_merge:
                    reader = PdfReader(item["path"])
                    for page in reader.pages:
                        if item["rotation"] != 0:
                            page.rotate(item["rotation"])
                        writer.add_page(page)
                output_path = get_unique_filename(
                    get_downloads_folder(), MERGED_OUTPUT_NAME
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
