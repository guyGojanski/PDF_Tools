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
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QIcon
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

        # --- Sidebar ---
        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(460)
        # תוקן: הסרנו את ה-setFixedHeight כדי שהסרגל ימתח לכל הגובה

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setSpacing(18)
        sidebar_layout.setContentsMargins(22, 20, 22, 20)

        sidebar_layout.addWidget(QLabel("Split Mode", objectName="SidebarTitle"))

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        modes = [
            ("Range", r"assets\ico\range.png"),
            ("Pages", r"assets\ico\Extractpages.png"),
            ("Size", r"assets\ico\filesize.png"),
        ]

        for i, (text, icon_path) in enumerate(modes):
            btn = QPushButton(text)
            btn.setObjectName("ModeButton")
            btn.setCheckable(True)
            btn.setMinimumHeight(80)

            # טעינת האייקון
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(40, 40))

            btn.clicked.connect(lambda _, idx=i: self.change_mode(idx))
            self.mode_group.addButton(btn, i)
            buttons_layout.addWidget(btn)

        sidebar_layout.addLayout(buttons_layout)

        self.sidebar_stack = QStackedWidget()
        self.sidebar_stack.addWidget(self._create_range_ui())
        self.sidebar_stack.addWidget(self._create_pages_ui())
        self.sidebar_stack.addWidget(self._create_size_ui())
        sidebar_layout.addWidget(self.sidebar_stack)

        sidebar_layout.addStretch()  # זה דוחף הכל למעלה

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
        layout.setSpacing(10)
        layout.setContentsMargins(0, 5, 0, 0)

        # 1. כפתורי הטאבים (Custom / Fixed)
        toggle_layout = QHBoxLayout()
        toggle_layout.setSpacing(10)

        self.btn_custom_range = QPushButton("Custom ranges")
        self.btn_custom_range.setProperty("class", "RangeTypeBtn")
        self.btn_custom_range.setCheckable(True)
        self.btn_custom_range.setChecked(True)
        self.btn_custom_range.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_fixed_range = QPushButton("Fixed ranges")
        self.btn_fixed_range.setProperty("class", "RangeTypeBtn")
        self.btn_fixed_range.setCheckable(True)
        self.btn_fixed_range.setCursor(Qt.CursorShape.PointingHandCursor)

        self.range_type_group = QButtonGroup(self)
        self.range_type_group.addButton(self.btn_custom_range, 0)
        self.range_type_group.addButton(self.btn_fixed_range, 1)
        self.range_type_group.setExclusive(True)

        self.btn_custom_range.clicked.connect(lambda: self._set_range_mode(custom=True))
        self.btn_fixed_range.clicked.connect(lambda: self._set_range_mode(custom=False))

        toggle_layout.addWidget(self.btn_custom_range)
        toggle_layout.addWidget(self.btn_fixed_range)
        layout.addLayout(toggle_layout)

        self.range_tabs = QStackedWidget()

        # --- לשונית Custom ---
        custom_widget = QWidget()
        custom_layout = QVBoxLayout(custom_widget)
        custom_layout.setContentsMargins(0, 5, 0, 0)
        custom_layout.setSpacing(10)

        # א. אזור הגלילה (מכיל רק את השורות)
        self.range_scroll = QScrollArea()
        self.range_scroll.setWidgetResizable(True)
        self.range_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.range_scroll.setObjectName("SidebarScroll")
        # גובה התחלתי קטן, נעדכן אותו דינמית
        self.range_scroll.setMinimumHeight(100)
        self.range_scroll.setMaximumHeight(500)

        self.range_scroll_content = QWidget()
        self.range_scroll_content.setObjectName("ScrollContent")
        self.range_scroll_content_layout = QVBoxLayout(self.range_scroll_content)
        self.range_scroll_content_layout.setSpacing(15)
        self.range_scroll_content_layout.setContentsMargins(0, 0, 5, 0)

        self.custom_rows_layout = QVBoxLayout()
        self.custom_rows_layout.setSpacing(10)
        self.range_scroll_content_layout.addLayout(self.custom_rows_layout)
        self.range_scroll_content_layout.addStretch()

        self.range_scroll.setWidget(self.range_scroll_content)
        custom_layout.addWidget(self.range_scroll)

        # ב. האזור הקבוע (מתחת לגלילה)
        fixed_bottom_area = QVBoxLayout()
        fixed_bottom_area.setSpacing(10)
        fixed_bottom_area.setContentsMargins(0, 5, 0, 5)

        add_btn = QPushButton("+ Add Range")
        add_btn.setObjectName("AddRangeBtn")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(lambda: self.add_range_row())

        self.merge_ranges_chk = QCheckBox("Merge all ranges in one PDF file")

        fixed_bottom_area.addWidget(add_btn)
        fixed_bottom_area.addWidget(self.merge_ranges_chk)

        custom_layout.addLayout(fixed_bottom_area)

        # זה חשוב: דוחף את כל האלמנטים למעלה, צמוד לראש
        custom_layout.addStretch()

        self.range_tabs.addWidget(custom_widget)

        # --- לשונית Fixed ---
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

    def _adjust_scroll_height(self):
        """פונקציה חכמה לחישוב גובה הגלילה"""
        if not hasattr(self, "range_scroll_content"):
            return

        # מחשבים את הגובה הרצוי לפי התוכן
        # נותנים למערכת רגע להתעדכן לפני החישוב
        QTimer.singleShot(10, self._perform_resize)

    def _perform_resize(self):
        content_height = self.range_scroll_content.sizeHint().height()
        # מוסיפים קצת "אוויר" שלא יחתוך
        new_height = content_height + 10
        # מגבילים למקסימום 500 פיקסלים
        final_height = min(new_height, 500)
        # אם יש מעט שורות, הגובה יהיה נמוך. אם יש הרבה, הוא יעצור ב-500.
        self.range_scroll.setFixedHeight(final_height)

    def _create_input_group(self, label_text: str, spinbox: QSpinBox) -> QFrame:
        frame = QFrame()
        frame.setProperty("class", "InputGroup")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        label = QLabel(label_text)
        layout.addWidget(label)

        spinbox.setProperty("class", "RangeSpin")
        layout.addWidget(spinbox)

        return frame

    def add_range_row(self, start: int = 1, end: int = None) -> None:
        if end is None:
            end = self.total_pages

        row_index = len(self.custom_rows) + 1

        card_frame = QFrame()
        card_frame.setProperty("class", "RangeRowCard")
        card_layout = QVBoxLayout(card_frame)
        card_layout.setSpacing(8)
        card_layout.setContentsMargins(10, 10, 10, 10)

        header_layout = QHBoxLayout()
        title = QLabel(f"Range {row_index}")
        title.setProperty("class", "RangeRowTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()

        if row_index > 1:
            remove_btn = QPushButton("✕")
            remove_btn.setProperty("class", "RemoveRangeBtn")
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.clicked.connect(lambda: self._remove_range_row(card_frame))
            header_layout.addWidget(remove_btn)

        card_layout.addLayout(header_layout)

        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(10)

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

        from_group = self._create_input_group("from page", start_spin)
        to_group = self._create_input_group("to", end_spin)

        inputs_layout.addWidget(from_group)
        inputs_layout.addWidget(to_group)
        card_layout.addLayout(inputs_layout)

        self.custom_rows_layout.addWidget(card_frame)
        self.custom_rows.append((start_spin, end_spin))
        self.update_preview()

        # עדכון גובה הגלילה
        self._adjust_scroll_height()

    def _remove_range_row(self, row_widget: QFrame) -> None:
        if len(self.custom_rows) <= 1:
            return

        index_to_remove = -1
        for i in range(self.custom_rows_layout.count()):
            if self.custom_rows_layout.itemAt(i).widget() == row_widget:
                index_to_remove = i
                break

        if index_to_remove != -1:
            self.custom_rows.pop(index_to_remove)
            self.custom_rows_layout.removeWidget(row_widget)
            row_widget.deleteLater()

            for i in range(self.custom_rows_layout.count()):
                widget = self.custom_rows_layout.itemAt(i).widget()
                if widget:
                    header_layout = widget.layout().itemAt(0).layout()
                    title_label = header_layout.itemAt(0).widget()
                    if title_label:
                        title_label.setText(f"Range {i + 1}")

            self.update_preview()
            # עדכון גובה הגלילה
            self._adjust_scroll_height()

    def _sync_range(self, start_spin: QSpinBox, end_spin: QSpinBox) -> None:
        if start_spin.value() > end_spin.value():
            end_spin.setValue(start_spin.value())

    def _set_range_mode(self, custom: bool) -> None:
        if custom and not self.custom_rows:
            self.add_range_row()
        self.range_tabs.setCurrentIndex(0 if custom else 1)

        self.btn_custom_range.setChecked(custom)
        self.btn_fixed_range.setChecked(not custom)

        self.update_preview()
        # לוודא שהגובה תקין במעבר בין טאבים
        if custom:
            self._adjust_scroll_height()

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
        if self.btn_fixed_range.isChecked():
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

                is_custom_mode = mode == 0 and self.btn_custom_range.isChecked()

                if is_custom_mode and self.merge_ranges_chk.isChecked():
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
