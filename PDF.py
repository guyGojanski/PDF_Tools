import sys
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGridLayout,
    QStackedWidget,
    QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap  # <--- הוספנו את QPixmap
from component.toolsForPDF import apply_stylesheet, cleanup_temp_folder
from component.file_picker import get_files
from modules.MergePDF import MergePreviewWindow
from modules.DeletePages import DeletePagesWindow
from modules.SplitPDF import SplitPDFWindow
from assets.config import *


class ToolCard(QFrame):
    def __init__(self, name, description, icon_path, tool_type, main_window):
        super().__init__()
        self.setObjectName("ToolCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(300)
        self.setMaximumWidth(450)
        self.setFixedHeight(TOOL_CARD_HEIGHT)
        self.tool_type = tool_type
        self.main_window = main_window
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        # === השינוי: טעינת תמונה ===
        self.icon_label = QLabel()
        self.icon_label.setObjectName("ToolIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # בדיקה אם זה קובץ PNG וטעינה שלו
        if icon_path and icon_path.endswith(".png"):
            pixmap = QPixmap(icon_path)
            # הקטנת התמונה לגודל מתאים (למשל 64x64)
            scaled_pixmap = pixmap.scaled(
                64,
                64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.icon_label.setPixmap(scaled_pixmap)
        else:
            # Fallback למקרה שאין תמונה (טקסט/אימוג'י)
            self.icon_label.setText(icon_path if icon_path else "")

        self.name_label = QLabel(name)
        self.name_label.setObjectName("ToolName")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label = QLabel(description)
        self.desc_label.setObjectName("ToolDesc")
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setWordWrap(True)
        self.btn = QPushButton("Start Working")
        self.btn.setObjectName("LaunchButton")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self.launch_tool)
        if not tool_type:
            self.btn.setEnabled(False)
            self.btn.setText("Coming Soon")
        layout.addWidget(self.icon_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.desc_label)
        layout.addStretch()
        layout.addWidget(self.btn)

    def launch_tool(self) -> None:
        if self.tool_type == "merge":
            self.main_window.launch_merge_tool()
        elif self.tool_type == "delete":
            self.main_window.launch_delete_tool()
        elif self.tool_type == "split":
            self.main_window.launch_split_tool()


class DashboardWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.tool_cards = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("DashboardScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.content_widget = QWidget()
        self.content_widget.setObjectName("DashboardContent")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(40, 30, 40, 40)
        self.content_layout.setSpacing(10)
        title = QLabel("PDF Solutions")
        title.setObjectName("DashboardTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Choose the professional tool you need right now")
        subtitle.setObjectName("DashboardSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(title)
        self.content_layout.addWidget(subtitle)
        self.grid_container = QWidget()
        self.grid_container.setObjectName("GridContainer")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(25)
        self.grid_layout.setContentsMargins(0, 20, 0, 0)
        self.grid_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter
        )
        tools = [
            (
                "Merge PDF",
                "Merge multiple PDF files into a single document flawlessly.",
                r"assets\ico\merge.png",
                "merge",
            ),
            (
                "Delete Pages",
                "Delete, reorder or rotate pages in your PDF file.",
                r"assets\ico\delete.png",
                "delete",
            ),
            (
                "Split PDF",
                "Split a PDF into multiple files based on your preferences.",
                r"assets\ico\split.png",
                "split",
            ),
            (
                "Compress PDF",
                "Reduce the file size of your PDF without losing quality.",
                "悼",  # כאן השארתי את הישן כי לא הבאת לו תמונה, אם יש לך תעדכן
                None,
            ),
        ]
        for name, desc, icon, tool_type in tools:
            card = ToolCard(name, desc, icon, tool_type, self.main_window)
            self.tool_cards.append(card)
        self.content_layout.addWidget(self.grid_container)
        self.content_layout.addStretch()
        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area)
        apply_stylesheet(self, STYLESHEET)

    def resizeEvent(self, event):
        self.reflow_grid()
        super().resizeEvent(event)

    def reflow_grid(self):
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        available_width = self.scroll_area.width() - 80
        card_width = 350 + 25
        cols = max(1, available_width // card_width)
        cols = min(cols, 2)
        for i, card in enumerate(self.tool_cards):
            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(card, row, col)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(MAIN_WINDOW_TITLE)
        self.setObjectName("DashboardWindow")
        start_w = getattr(
            sys.modules.get("assets.config"), "MAIN_WINDOW_START_WIDTH", 1200
        )
        start_h = getattr(
            sys.modules.get("assets.config"), "MAIN_WINDOW_START_HEIGHT", 800
        )
        min_w = getattr(sys.modules.get("assets.config"), "MAIN_WINDOW_MIN_WIDTH", 900)
        min_h = getattr(sys.modules.get("assets.config"), "MAIN_WINDOW_MIN_HEIGHT", 700)
        self.resize(start_w, start_h)
        self.setMinimumSize(min_w, min_h)
        apply_stylesheet(self, STYLESHEET)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.dashboard = DashboardWidget(self)
        self.stack.addWidget(self.dashboard)

    def launch_merge_tool(self) -> None:
        self._launch_tool_generic("merge", MERGE_MAX_FILES, MERGE_TEMP_FOLDER)

    def launch_delete_tool(self) -> None:
        self._launch_tool_generic("delete", DELETE_MAX_FILES, DELETE_TEMP_FOLDER)

    def launch_split_tool(self) -> None:
        self._launch_tool_generic("split", SPLIT_MAX_FILES, SPLIT_TEMP_FOLDER)

    def _launch_tool_generic(
        self, tool_type: str, max_files: int, temp_folder: str
    ) -> None:
        files = get_files(max_files=max_files, target_folder=temp_folder)
        if not files:
            cleanup_temp_folder(temp_folder)
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        tool = None
        try:
            if tool_type == "merge":
                tool = MergePreviewWindow(files, temp_folder, max_files)
            elif tool_type == "delete":
                tool = DeletePagesWindow(files[0], temp_folder)
            elif tool_type == "split":
                tool = SplitPDFWindow(files[0], temp_folder)
            if tool:
                tool.back_to_dashboard.connect(self.return_to_dashboard)
                self.stack.addWidget(tool)
                self.stack.setCurrentWidget(tool)
        except Exception as e:
            print(f"Error launching tool {tool_type}: {e}")
            cleanup_temp_folder(temp_folder)
        finally:
            QApplication.restoreOverrideCursor()

    def return_to_dashboard(self):
        current_widget = self.stack.currentWidget()
        self.stack.setCurrentWidget(self.dashboard)
        if current_widget != self.dashboard:
            self.stack.removeWidget(current_widget)
            current_widget.deleteLater()


def main():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
