import sys
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
from PyQt6.QtGui import QPixmap
from component.toolsForPDF import apply_stylesheet, cleanup_temp_folder
from component.file_picker import get_files
from modules.MergePDF import MergePreviewWindow
from modules.DeletePages import DeletePagesWindow
from modules.SplitPDF import SplitPDFWindow
from assets.config import *


class ToolCard(QFrame):
    def __init__(self, name, description, icon_path, tool_type, main_window):
        super().__init__()
        self.setObjectName("ToolCardFrame")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(300)
        self.setMaximumWidth(450)
        self.setFixedHeight(TOOL_CARD_HEIGHT)
        self.tool_type = tool_type
        self.main_window = main_window
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        self.icon_label = QLabel()
        self.icon_label.setObjectName("ToolCardIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if icon_path and icon_path.endswith(".png"):
            pixmap = QPixmap(icon_path)
            scaled_pixmap = pixmap.scaled(
                64,
                64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.icon_label.setPixmap(scaled_pixmap)
        else:
            self.icon_label.setText(icon_path if icon_path else "")
        self.name_label = QLabel(name)
        self.name_label.setObjectName("ToolCardTitle")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label = QLabel(description)
        self.desc_label.setObjectName("ToolCardSubtitle")
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setWordWrap(True)
        self.launch_button = QPushButton("Start Working")
        self.launch_button.setObjectName("ToolCardActionButton")
        self.launch_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.launch_button.clicked.connect(self.launch_tool)
        if not tool_type:
            self.launch_button.setEnabled(False)
            self.launch_button.setText("Coming Soon")
        layout.addWidget(self.icon_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.desc_label)
        layout.addStretch()
        layout.addWidget(self.launch_button)

    def launch_tool(self) -> None:
        tool_map = {
            "merge": self.main_window.launch_merge_tool,
            "delete": self.main_window.launch_delete_tool,
            "split": self.main_window.launch_split_tool,
        }
        if self.tool_type in tool_map:
            tool_map[self.tool_type]()


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
        title.setObjectName("DashboardHeading")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Choose the professional tool you need right now")
        subtitle.setObjectName("DashboardSubheading")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(title)
        self.content_layout.addWidget(subtitle)
        self.grid_container = QWidget()
        self.grid_container.setObjectName("CardGrid")
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
                "悼",
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
        self.resize(MAIN_WINDOW_START_WIDTH, MAIN_WINDOW_START_HEIGHT)
        self.setMinimumSize(MAIN_WINDOW_MIN_WIDTH, MAIN_WINDOW_MIN_HEIGHT)
        apply_stylesheet(self, STYLESHEET)
        
        cleanup_temp_folder(MERGE_TEMP_FOLDER)
        cleanup_temp_folder(DELETE_TEMP_FOLDER)
        cleanup_temp_folder(SPLIT_TEMP_FOLDER)
        cleanup_temp_folder(FILE_PICKER_DEFAULT_FOLDER)
        
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.dashboard = DashboardWidget(self)
        self.stack.addWidget(self.dashboard)

    def launch_merge_tool(self) -> None:
        self._launch_tool_generic("merge", MAX_MERGE_FILES, MERGE_TEMP_FOLDER)

    def launch_delete_tool(self) -> None:
        self._launch_tool_generic("delete", MAX_DELETE_FILES, DELETE_TEMP_FOLDER)

    def launch_split_tool(self) -> None:
        self._launch_tool_generic("split", MAX_SPLIT_FILES, SPLIT_TEMP_FOLDER)

    def _launch_tool_generic(
        self, tool_type: str, max_files: int, temp_folder: str
    ) -> None:
        files = get_files(max_files=max_files, target_folder=temp_folder)
        if not files:
            cleanup_temp_folder(temp_folder)
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        tool_map = {
            "merge": lambda: MergePreviewWindow(files, temp_folder, max_files),
            "delete": lambda: DeletePagesWindow(files[0], temp_folder),
            "split": lambda: SplitPDFWindow(files[0], temp_folder),
        }
        try:
            if tool_type in tool_map:
                tool = tool_map[tool_type]()
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
    
    def closeEvent(self, event):
        cleanup_temp_folder(MERGE_TEMP_FOLDER)
        cleanup_temp_folder(DELETE_TEMP_FOLDER)
        cleanup_temp_folder(SPLIT_TEMP_FOLDER)
        cleanup_temp_folder(FILE_PICKER_DEFAULT_FOLDER)
        super().closeEvent(event)


def main():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
