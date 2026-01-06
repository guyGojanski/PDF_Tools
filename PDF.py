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
    QMessageBox,
)
from PyQt6.QtCore import Qt
from component.toolsForPDF import apply_stylesheet, cleanup_temp_folder
from component.file_picker import get_files
from modules.MergePDF import MergePreviewWindow
from modules.DeletePages import DeletePagesWindow
from assets.config import (
    MAIN_WINDOW_TITLE,
    MAIN_WINDOW_WIDTH,
    MAIN_WINDOW_HEIGHT,
    STYLESHEET_MAIN,
    TOOL_CARD_WIDTH,
    TOOL_CARD_HEIGHT,
    MERGE_MAX_FILES,
    MERGE_TEMP_FOLDER,
    DELETE_MAX_FILES,
    DELETE_TEMP_FOLDER,
) 
    


class ToolCard(QFrame):
    def __init__(self, name, description, icon, tool_type, main_window):
        super().__init__()
        self.setObjectName("ToolCard")
        self.setFixedSize(TOOL_CARD_WIDTH, TOOL_CARD_HEIGHT)
        self.tool_type = tool_type
        self.main_window = main_window
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        self.icon_label = QLabel(icon)
        self.icon_label.setObjectName("ToolIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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


class DashboardWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 40)
        layout.setSpacing(10)
        title = QLabel("PDF Solutions")
        title.setObjectName("DashboardTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Choose the professional tool you need right now")
        subtitle.setObjectName("DashboardSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        grid = QGridLayout()
        grid.setSpacing(25)
        tools = [
            (
                "Merge PDF",
                "Merge multiple PDF files into a single document flawlessly.",
                "📚",
                "merge",
            ),
            (
                "Delete Pages",
                "Delete, reorder or rotate pages in your PDF file.",
                "✂️",
                "delete",
            ),
            (
                "Split PDF",
                "Split a PDF into multiple files based on your preferences.",
                "🧩",
                None,
            ),
            (
                "Compress PDF",
                "Reduce the file size of your PDF without losing quality.",
                "📉",
                None,
            ),
        ]
        for i, (name, desc, icon, tool_type) in enumerate(tools):
            card = ToolCard(name, desc, icon, tool_type, self.main_window)
            row, col = i // 2, i % 2
            grid.addWidget(card, row, col)
        layout.addLayout(grid)
        layout.addStretch()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(MAIN_WINDOW_TITLE)
        self.setObjectName("DashboardWindow")
        self.setFixedSize(MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT)
        apply_stylesheet(self, STYLESHEET_MAIN)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.dashboard = DashboardWidget(self)
        self.stack.addWidget(self.dashboard)

    def launch_merge_tool(self) -> None:
        self._launch_tool_generic(
            "merge", max_files=MERGE_MAX_FILES, temp_folder=MERGE_TEMP_FOLDER
        )

    def launch_delete_tool(self) -> None:
        self._launch_tool_generic(
            "delete", max_files=DELETE_MAX_FILES, temp_folder=DELETE_TEMP_FOLDER
        )

    def _launch_tool_generic(
        self, tool_type: str, max_files: int, temp_folder: str
    ) -> None:
        from modules.MergePDF import MergePreviewWindow
        from modules.DeletePages import DeletePagesWindow

        files = get_files(max_files=max_files, target_folder=temp_folder)
        if not files:
            cleanup_temp_folder(temp_folder)
            return
        if tool_type == "merge":
            tool = MergePreviewWindow(files, temp_folder)
        else:
            tool = DeletePagesWindow(files[0], temp_folder)
        tool.back_to_dashboard.connect(self.return_to_dashboard)
        self.stack.addWidget(tool)
        self.stack.setCurrentWidget(tool)

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
