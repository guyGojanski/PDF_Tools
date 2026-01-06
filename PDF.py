import sys
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt
from component.toolsForPDF import apply_stylesheet

class ToolCard(QFrame):
    def __init__(self, name, description, icon, script_name):
        super().__init__()
        self.setObjectName("ToolCard")
        self.setFixedSize(300, 240)
        self.script_name = script_name
        
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
        self.btn.clicked.connect(self.launch_script)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.desc_label)
        layout.addStretch()
        layout.addWidget(self.btn)

    def launch_script(self):
        if not self.script_name:
            return
        try:
            subprocess.Popen([sys.executable, self.script_name])
        except Exception as e:
            print(f"Critical error: {e}")

class PDFDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Master Suite")
        self.setObjectName("DashboardWindow")
        self.setFixedSize(1000, 700)
        
        apply_stylesheet(self, "style_app.qss")
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 30, 40, 40)
        main_layout.setSpacing(10)

        title = QLabel("PDF Solutions")
        title.setObjectName("DashboardTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("Choose the professional tool you need right now")
        subtitle.setObjectName("DashboardSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setSpacing(25)

        tools = [
            ("Merge PDF", "Merge multiple PDF files into a single document flawlessly.", "📚", "MergePDF.py"),
            ("Delete Pages", "Delete, reorder or rotate pages in your PDF file.", "✂️", "DeletePages.py"),
            ("PDF to Text", "Extract text from PDF documents using OCR technology.", "📝", ""),
            ("Compress PDF", "Reduce the file size of your PDF without losing quality.", "📉", "")
        ]

        for i, (name, desc, icon, script) in enumerate(tools):
            card = ToolCard(name, desc, icon, script)
            if not script:
                card.btn.setEnabled(False)
                card.btn.setText("Coming Soon")
            
            row, col = i // 2, i % 2
            grid.addWidget(card, row, col)

        main_layout.addLayout(grid)
        main_layout.addStretch()

def main():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    window = PDFDashboard()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()