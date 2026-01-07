import io
import os
import re
import fitz
from typing import List, Tuple
from pypdf import PdfWriter, PdfReader
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt
from component.header_bar import HeaderBar
from component.toolsForPDF import (
    BaseToolWindow,
    button_operation,
    cleanup_temp_folder,
    get_downloads_folder,
    get_pdf_thumbnail,
    get_unique_filename,
)
from assets.config import SPLIT_HEADER_TITLE
class RangeGroupWidget(QFrame):
    def __init__(
        self, file_path: str, start_page: int, end_page: int, group_index: int
    ):
        super().__init__()
        self.setObjectName("RangeGroup")
        self.setFixedSize(240, 190)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        title_label = QLabel(f"Range {group_index}")
        title_label.setObjectName("GroupTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        thumbs_layout = QHBoxLayout()
        thumbs_layout.setSpacing(10)
        thumb1 = self._create_thumb(file_path, start_page)
        thumbs_layout.addWidget(thumb1)
        if end_page > start_page:
            dots = QLabel("…")
            dots.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumbs_layout.addWidget(dots)
            thumb2 = self._create_thumb(file_path, end_page)
            thumbs_layout.addWidget(thumb2)
        layout.addLayout(thumbs_layout)
        pages_label = QLabel(f"Pages: {start_page + 1}-{end_page + 1}")
        pages_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(pages_label)
    def _create_thumb(self, file_path: str, page_num: int) -> QLabel:
        lbl = QLabel()
        lbl.setObjectName("PageThumb")
        lbl.setFixedSize(70, 92)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = get_pdf_thumbnail(file_path, page_num, width=70, height=92)
        if pix:
            lbl.setPixmap(pix)
        else:
            lbl.setText(str(page_num + 1))
        return lbl
class SplitPDFWindow(BaseToolWindow):
    def __init__(self, file_path: str, temp_folder: str):
        super().__init__(temp_folder, SPLIT_HEADER_TITLE)
        self.file_path = file_path
        self.doc = fitz.open(file_path)
        self.total_pages = len(self.doc)
        self.file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        self.ranges_to_split: List[Tuple[int, int]] = []
        self.custom_rows: List[Tuple[QSpinBox, QSpinBox]] = []
        self._init_ui()
        self.mode_group.button(0).setChecked(True)
        self._set_range_mode(custom=True)
        self.update_preview()
    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(0, 0, 0, 20)
        self.header = HeaderBar(self.header_title)
        self.header.back_clicked.connect(self.go_back)
        main_layout.addWidget(self.header)
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("MergeScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.grid_container = QWidget()
        self.grid_container.setObjectName("GridContainer")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)
        self.grid_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.scroll_area.setWidget(self.grid_container)
        content_layout.addWidget(self.scroll_area, stretch=7)
        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(340)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setSpacing(18)
        sidebar_layout.setContentsMargins(22, 20, 22, 20)
        sidebar_layout.addWidget(QLabel("Split Mode", objectName="SidebarTitle"))
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        modes = [("Range", "✂️"), ("Pages", "📄"), ("Size", "⚖️")]
        for i, (text, icon) in enumerate(modes):
            btn = QPushButton(f"{icon}\n{text}")
            btn.setObjectName("ModeButton")
            btn.setCheckable(True)
            btn.setMinimumHeight(60)
            btn.clicked.connect(lambda _, idx=i: self.change_mode(idx))
            self.mode_group.addButton(btn, i)
            buttons_layout.addWidget(btn)
        sidebar_layout.addLayout(buttons_layout)
        self.sidebar_stack = QStackedWidget()
        self.sidebar_stack.addWidget(self._create_range_ui())
        self.sidebar_stack.addWidget(self._create_pages_ui())
        self.sidebar_stack.addWidget(self._create_size_ui())
        sidebar_layout.addWidget(self.sidebar_stack)
        sidebar_layout.addStretch()
        self.split_btn = QPushButton("Split PDF")
        self.split_btn.setObjectName("MergeButton")
        self.split_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.split_btn.setMinimumHeight(52)
        self.split_btn.clicked.connect(self.perform_split)
        sidebar_layout.addWidget(self.split_btn)
        content_layout.addWidget(self.sidebar)
        main_layout.addLayout(content_layout)
    def _create_range_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        toggle_layout = QHBoxLayout()
        self.rb_custom = QRadioButton("Custom ranges")
        self.rb_fixed = QRadioButton("Fixed ranges")
        self.rb_custom.toggled.connect(
            lambda checked: self._set_range_mode(custom=checked)
        )
        toggle_layout.addWidget(self.rb_custom)
        toggle_layout.addWidget(self.rb_fixed)
        layout.addLayout(toggle_layout)
        self.range_tabs = QStackedWidget()
        custom_widget = QWidget()
        custom_layout = QVBoxLayout(custom_widget)
        custom_layout.setSpacing(10)
        self.custom_rows_layout = QVBoxLayout()
        self.custom_rows_layout.setSpacing(8)
        custom_layout.addLayout(self.custom_rows_layout)
        add_btn = QPushButton("+ Add Range")
        add_btn.setObjectName("AddButton")
        add_btn.clicked.connect(lambda: self.add_range_row())
        custom_layout.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self.merge_ranges_chk = QCheckBox("Merge all ranges in one PDF file")
        custom_layout.addWidget(self.merge_ranges_chk)
        custom_layout.addStretch()
        self.range_tabs.addWidget(custom_widget)
        fixed_widget = QWidget()
        fixed_layout = QVBoxLayout(fixed_widget)
        fixed_layout.setSpacing(10)
        fixed_layout.addWidget(QLabel("Split into files of X pages:"))
        self.fixed_spin = QSpinBox()
        self.fixed_spin.setRange(1, max(1, self.total_pages))
        self.fixed_spin.setValue(1)
        self.fixed_spin.valueChanged.connect(self.update_preview)
        fixed_layout.addWidget(self.fixed_spin)
        fixed_layout.addStretch()
        self.range_tabs.addWidget(fixed_widget)
        layout.addWidget(self.range_tabs)
        return widget
    def add_range_row(self, start: int = 1, end: int = None) -> None:
        if end is None:
            end = self.total_pages
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)
        start_spin = QSpinBox()
        start_spin.setRange(1, self.total_pages)
        start_spin.setValue(start)
        end_spin = QSpinBox()
        end_spin.setRange(1, self.total_pages)
        end_spin.setValue(min(end, self.total_pages))
        start_spin.valueChanged.connect(
            lambda _: self._sync_range(start_spin, end_spin)
        )
        end_spin.valueChanged.connect(lambda _: self._sync_range(start_spin, end_spin))
        start_spin.valueChanged.connect(self.update_preview)
        end_spin.valueChanged.connect(self.update_preview)
        row_layout.addWidget(QLabel("from page"))
        row_layout.addWidget(start_spin)
        row_layout.addWidget(QLabel("to"))
        row_layout.addWidget(end_spin)
        remove_btn = QPushButton("×")
        remove_btn.setFixedWidth(26)
        remove_btn.clicked.connect(lambda: self._remove_range_row(row_widget))
        row_layout.addWidget(remove_btn)
        self.custom_rows_layout.addWidget(row_widget)
        self.custom_rows.append((start_spin, end_spin))
        self.update_preview()
    def _remove_range_row(self, row_widget: QWidget) -> None:
        if len(self.custom_rows) <= 1:
            return
        for i, (start_spin, end_spin) in enumerate(self.custom_rows):
            if start_spin.parent() is row_widget:
                self.custom_rows.pop(i)
                break
        self.custom_rows_layout.removeWidget(row_widget)
        row_widget.deleteLater()
        self.update_preview()
    def _sync_range(self, start_spin: QSpinBox, end_spin: QSpinBox) -> None:
        if start_spin.value() > end_spin.value():
            end_spin.setValue(start_spin.value())
    def _set_range_mode(self, custom: bool) -> None:
        if custom and not self.custom_rows:
            self.add_range_row()
        self.range_tabs.setCurrentIndex(0 if custom else 1)
        self.rb_custom.setChecked(custom)
        self.rb_fixed.setChecked(not custom)
        self.update_preview()
    def _create_pages_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        self.rb_extract_all = QRadioButton("Extract all pages")
        self.rb_extract_all.setChecked(True)
        self.rb_extract_all.toggled.connect(self.update_preview)
        self.rb_select_pages = QRadioButton("Select pages")
        self.rb_select_pages.toggled.connect(self.update_preview)
        self.pages_input = QLineEdit()
        self.pages_input.setPlaceholderText("e.g. 1, 3, 5-8")
        self.pages_input.setEnabled(False)
        self.pages_input.textChanged.connect(self.update_preview)
        self.rb_select_pages.toggled.connect(self.pages_input.setEnabled)
        layout.addWidget(self.rb_extract_all)
        layout.addWidget(self.rb_select_pages)
        layout.addWidget(self.pages_input)
        layout.addStretch()
        return widget
    def _create_size_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        info_label = QLabel(
            f"File Size: {self.file_size_mb:.2f} MB\nTotal Pages: {self.total_pages}"
        )
        info_label.setObjectName("SizeInfoLabel")
        layout.addWidget(info_label)
        layout.addWidget(QLabel("Max size per file:"))

        size_input_layout = QHBoxLayout()
        size_input_layout.setSpacing(8)
        self.size_spin = QDoubleSpinBox()
        self.size_spin.setRange(0.1, 9999)
        self.size_spin.setValue(1.0)
        self.size_spin.valueChanged.connect(self.update_preview)
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["MB", "KB"])
        self.unit_combo.currentIndexChanged.connect(self.update_preview)
        size_input_layout.addWidget(self.size_spin)
        size_input_layout.addWidget(self.unit_combo)
        layout.addLayout(size_input_layout)
        layout.addWidget(QLabel("* Preview uses average page size approximation"))
        layout.addStretch()
        return widget
    def change_mode(self, index: int) -> None:
        self.sidebar_stack.setCurrentIndex(index)
        self.update_preview()
    def _collect_ranges_range_mode(self) -> List[Tuple[int, int]]:
        if self.rb_fixed.isChecked():
            step = max(1, self.fixed_spin.value())
            return [
                (i, min(i + step - 1, self.total_pages - 1))
                for i in range(0, self.total_pages, step)
            ]
        ranges: List[Tuple[int, int]] = []
        for start_spin, end_spin in self.custom_rows:
            s, e = start_spin.value(), end_spin.value()
            if s <= e:
                ranges.append((s - 1, e - 1))
        return ranges
    def _collect_ranges_pages_mode(self) -> List[Tuple[int, int]]:
        if self.rb_extract_all.isChecked():
            return [(i, i) for i in range(self.total_pages)]
        pages = self._parse_page_list(self.pages_input.text())
        return [(p, p) for p in pages]
    def _collect_ranges_size_mode(self) -> List[Tuple[int, int]]:
        target_mb = self.size_spin.value()
        if self.unit_combo.currentText() == "KB":
            target_mb /= 1024
        avg_page_mb = self.file_size_mb / self.total_pages if self.total_pages else 0.1
        pages_per_file = max(1, int(target_mb / avg_page_mb)) if avg_page_mb > 0 else 1
        return [
            (i, min(i + pages_per_file - 1, self.total_pages - 1))
            for i in range(0, self.total_pages, pages_per_file)
        ]
    def update_preview(self) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        mode = self.mode_group.checkedId()
        if mode == 0:
            self.ranges_to_split = self._collect_ranges_range_mode()
        elif mode == 1:
            self.ranges_to_split = self._collect_ranges_pages_mode()
        elif mode == 2:
            self.ranges_to_split = self._collect_ranges_size_mode()
        else:
            self.ranges_to_split = []
        cols = 3
        for idx, (start, end) in enumerate(self.ranges_to_split):
            widget = RangeGroupWidget(self.file_path, start, end, idx + 1)
            self.grid_layout.addWidget(widget, idx // cols, idx % cols)
        enabled = len(self.ranges_to_split) > 0
        self.split_btn.setEnabled(enabled)
        if enabled:
            self.split_btn.setText(f"Split into {len(self.ranges_to_split)} Files")
        else:
            self.split_btn.setText("Split PDF")
    def _parse_page_list(self, text: str) -> List[int]:
        pages: List[int] = []
        cleaned = re.sub(r"[^0-9,\-]", "", text or "")
        for part in cleaned.split(","):
            if not part:
                continue
            if "-" in part:
                try:
                    start_str, end_str = part.split("-", 1)
                    s, e = int(start_str), int(end_str)
                    if 1 <= s <= e <= self.total_pages:
                        pages.extend(range(s - 1, e))
                except ValueError:
                    continue
            else:
                try:
                    p = int(part)
                    if 1 <= p <= self.total_pages:
                        pages.append(p - 1)
                except ValueError:
                    continue
        return sorted(list(dict.fromkeys(pages)))
    def perform_split(self) -> None:
        if not self.ranges_to_split:
            return
        mode = self.mode_group.checkedId()
        if mode == 2:
            self._split_by_size_greedy()
            return

        with button_operation(self.split_btn, "Splitting...", "Split PDF"):
            QApplication.processEvents()
            try:
                reader = PdfReader(self.file_path)
                base_name = os.path.splitext(os.path.basename(self.file_path))[0]
                save_dir = get_downloads_folder()
                created_files: List[str] = []
                if (
                    mode == 0
                    and self.rb_custom.isChecked()
                    and self.merge_ranges_chk.isChecked()
                ):
                    writer = PdfWriter()
                    for start, end in self.ranges_to_split:
                        for p in range(start, end + 1):
                            writer.add_page(reader.pages[p])
                    out_path = get_unique_filename(
                        save_dir, f"{base_name}_merged_split.pdf"
                    )
                    with open(out_path, "wb") as f:
                        writer.write(f)
                    created_files.append(out_path)
                else:
                    for idx, (start, end) in enumerate(self.ranges_to_split):
                        writer = PdfWriter()
                        for p in range(start, end + 1):
                            writer.add_page(reader.pages[p])
                        out_path = get_unique_filename(
                            save_dir, f"{base_name}_part_{idx + 1}.pdf"
                        )
                        with open(out_path, "wb") as f:
                            writer.write(f)
                        created_files.append(out_path)
                QMessageBox.information(
                    self,
                    "Success",
                    f"Created {len(created_files)} files in Downloads folder.",
                )
                self.go_back()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
    def _split_by_size_greedy(self) -> None:
        target_mb = self.size_spin.value()
        if self.unit_combo.currentText() == "KB":
            target_mb /= 1024
        limit_bytes = target_mb * 1024 * 1024 * 0.95
        with button_operation(self.split_btn, "Calculating...", "Split PDF"):
            QApplication.processEvents()
            try:
                reader = PdfReader(self.file_path)
                base_name = os.path.splitext(os.path.basename(self.file_path))[0]
                save_dir = get_downloads_folder()
                current_writer = PdfWriter()
                current_page_count = 0
                file_index = 1
                created_files: List[str] = []
                for page in reader.pages:
                    current_writer.add_page(page)
                    current_page_count += 1
                    temp_buffer = io.BytesIO()
                    current_writer.write(temp_buffer)
                    current_size = temp_buffer.tell()
                    if current_size > limit_bytes and current_page_count > 1:
                        save_writer = PdfWriter()
                        for p_idx in range(len(current_writer.pages) - 1):
                            save_writer.add_page(current_writer.pages[p_idx])
                        out_path = get_unique_filename(
                            save_dir, f"{base_name}_part_{file_index}.pdf"
                        )
                        with open(out_path, "wb") as f:
                            save_writer.write(f)
                        created_files.append(out_path)
                        file_index += 1
                        current_writer = PdfWriter()
                        current_writer.add_page(page)
                        current_page_count = 1
                if len(current_writer.pages) > 0:
                    out_path = get_unique_filename(
                        save_dir, f"{base_name}_part_{file_index}.pdf"
                    )
                    with open(out_path, "wb") as f:
                        current_writer.write(f)
                    created_files.append(out_path)
                QMessageBox.information(
                    self,
                    "Success",
                    f"Created {len(created_files)} files by size.",
                )
                self.go_back()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Size Split Error: {str(e)}")
    def closeEvent(self, event) -> None:
        try:
            if self.doc:
                self.doc.close()
        finally:
            cleanup_temp_folder(self.temp_folder)
            super().closeEvent(event)
