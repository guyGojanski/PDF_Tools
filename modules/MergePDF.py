import os
from PyQt6.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QApplication,
    QDialog,
    QLineEdit,
    QWidget,
    QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from pypdf import PdfWriter, PdfReader
from component.pdf_grid import PDFGrid
from component.header_bar import HeaderBar
from component.toolsForPDF import *
from assets.config import *


class PasswordInputDialog(QDialog):
    def __init__(self, filename, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Password Required")
        self.setObjectName("PasswordPromptDialog")
        self.setFixedSize(PASSWORD_DIALOG_WIDTH, PASSWORD_DIALOG_HEIGHT)
        self.password = None
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        title = QLabel("File requires password")
        title.setObjectName("DialogTitleLabel")
        layout.addWidget(title)
        file_label = QLabel(f"File: {filename}")
        file_label.setObjectName("FileNameLabel")
        file_label.setWordWrap(True)
        layout.addWidget(file_label)
        input_container = QHBoxLayout()
        input_container.setSpacing(5)
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter Password")
        self.input_field.setEchoMode(QLineEdit.EchoMode.Password)
        input_container.addWidget(self.input_field)
        self.visibility_button = QPushButton()
        self.visibility_button.setIcon(QIcon("assets/ico/hiddeneye.png"))
        self.visibility_button.setObjectName("PasswordToggleButton")
        self.visibility_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.visibility_button.clicked.connect(self.toggle_visibility)
        input_container.addWidget(self.visibility_button)
        layout.addLayout(input_container)
        self.submit_button = QPushButton("Unlock & Add")
        self.submit_button.setObjectName("SubmitButton")
        self.submit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.submit_button.clicked.connect(self.verify)
        layout.addWidget(self.submit_button)

    def toggle_visibility(self):
        if self.input_field.echoMode() == QLineEdit.EchoMode.Password:
            self.input_field.setEchoMode(QLineEdit.EchoMode.Normal)
            self.visibility_button.setIcon(QIcon("assets/ico/eye.png"))
        else:
            self.input_field.setEchoMode(QLineEdit.EchoMode.Password)
            self.visibility_button.setIcon(QIcon("assets/ico/hiddeneye.png"))

    def verify(self):
        pwd = self.input_field.text().strip()
        if not pwd:
            QMessageBox.warning(self, "Empty Password", "Please enter a password or close this dialog to skip.")
            return
        self.password = pwd
        self.accept()


class MergePreviewWindow(BaseToolWindow):
    def __init__(self, file_list_paths, temp_folder, max_files=MAX_MERGE_FILES):
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
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(0, 0, 0, 20)
        self.header = HeaderBar(self.header_title)
        self.header.back_clicked.connect(self.go_back)
        main_layout.addWidget(self.header)
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(20, 0, 20, 0)
        center_layout.setSpacing(12)
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        self.title_label = QLabel()
        self.title_label.setObjectName("ScreenTitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.add_btn = QPushButton("+")
        self.add_btn.setObjectName("AddFileButton")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setFixedSize(ADD_BUTTON_SIZE, ADD_BUTTON_SIZE)
        self.add_btn.clicked.connect(self.on_add_clicked)
        title_row.addStretch()
        title_row.addWidget(self.title_label)
        title_row.addStretch()
        title_row.addWidget(self.add_btn)
        center_layout.addLayout(title_row)
        self.pdf_grid = PDFGrid(initial_items, max_items=self.max_files)
        self.pdf_grid.items_changed.connect(self.update_title)
        center_layout.addWidget(self.pdf_grid)
        content_layout.addWidget(center_container, stretch=1)
        self.sidebar = QWidget()
        self.sidebar.setObjectName("ToolSidebar")
        self.sidebar.setFixedWidth(SIDEBAR_WIDTH)
        self.sidebar.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setSpacing(14)
        sidebar_layout.setContentsMargins(22, 18, 22, 18)
        sidebar_layout.addWidget(QLabel("Merge PDF", objectName="SidebarTitle"))
        self.count_label = QLabel()
        self.count_label.setObjectName("SidebarStatText")
        sidebar_layout.addWidget(self.count_label)
        hint_label = QLabel(
            "Tip: Drag cards to reorder before merging. Use + to add more files."
        )
        hint_label.setObjectName("SidebarHintText")
        hint_label.setWordWrap(True)
        sidebar_layout.addWidget(hint_label)
        sidebar_layout.addStretch()
        self.merge_btn = QPushButton("Merge PDF Now")
        self.merge_btn.setObjectName("PrimaryActionButton")
        self.merge_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.merge_btn.setMinimumHeight(PRIMARY_BUTTON_HEIGHT)
        self.merge_btn.clicked.connect(self.perform_merge)
        sidebar_layout.addWidget(self.merge_btn)
        content_layout.addWidget(self.sidebar, stretch=0)
        main_layout.addLayout(content_layout)
        self.update_title()

    def update_title(self):
        count = len(self.pdf_grid.get_items())
        self.title_label.setText(f"Selected {count} / {self.max_files} Files")
        if hasattr(self, "count_label"):
            self.count_label.setText(f"Files: {count} / {self.max_files}")

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
        progress = create_progress_dialog(
            self, "Please Wait", "Processing files...", len(files_to_process)
        )
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
                    pages_indices = list(range(len(reader.pages)))
                    rotations = {i: item["rotation"] for i in pages_indices}
                    write_pdf_with_rotation(writer, reader, pages_indices, rotations)
                if save_pdf_with_success(
                    writer, MERGED_OUTPUT_NAME, self, f"Saved at Downloads folder"
                ):
                    self.go_back()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
            finally:
                cleanup_temp_folder(self.temp_folder)
