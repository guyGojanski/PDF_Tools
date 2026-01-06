import sys
import os
import shutil
import fitz  # PyMuPDF
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from pypdf import PdfWriter, PdfReader

from component.pdf_grid import PDFGrid
from component.toolsForPDF import (
    get_downloads_folder,
    open_file,
    apply_stylesheet,
    cleanup_temp_folder,
)
# ייבוא רכיב בחירת הקבצים המקורי
from component.file_picker import get_files

class DeletePagesWindow(QWidget):
    def __init__(self, file_path, temp_folder):
        super().__init__()
        self.file_path = file_path
        self.temp_folder = temp_folder
        
        # פירוק הקובץ הבודד לעמודים עבור ה-Grid
        doc = fitz.open(file_path)
        num_pages = len(doc)
        doc.close()

        # יצירת רשימת פריטים שבה כל פריט הוא עמוד מאותו קובץ
        self.pages_data = [
            {'path': file_path, 'page': i, 'rotation': 0, 'marked': False} 
            for i in range(num_pages)
        ]

        self.setWindowTitle("PDF Page Editor")
        self.setObjectName("MergePreviewWindow")
        self.setMinimumSize(1000, 700)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        apply_stylesheet(self, "style.qss")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        header = QHBoxLayout()
        self.title_label = QLabel(f"Editing: {os.path.basename(self.file_path)}")
        self.title_label.setObjectName("MergeTitle")
        header.addStretch()
        header.addWidget(self.title_label)
        header.addStretch()
        layout.addLayout(header)

        # יצירת הגריד עם הגדרה של interactive_delete=True לסימון ב-X
        self.pdf_grid = PDFGrid(
            self.pages_data, 
            max_items=2000, 
            on_delete_callback=self.toggle_mark
        )
        layout.addWidget(self.pdf_grid)

        self.save_btn = QPushButton("Save Changes (Remove Marked Pages)")
        self.save_btn.setObjectName("MergeButton")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setMinimumHeight(60)
        self.save_btn.clicked.connect(self.perform_save)
        layout.addWidget(self.save_btn)

    def toggle_mark(self, item_data):
        item_data['marked'] = not item_data.get('marked', False)
        card = self.pdf_grid.get_card_by_data(item_data)
        if card:
            if item_data['marked']:
                card.set_overlay("X")
            else:
                card.set_overlay("", visible=False)

    def perform_save(self):
        items = self.pdf_grid.get_items()
        pages_to_keep = [item for item in items if not item.get('marked', False)]
        
        if not pages_to_keep:
            QMessageBox.warning(self, "Error", "Cannot delete all pages!")
            return

        self.save_btn.setText("Saving...")
        self.save_btn.setEnabled(False)
        QApplication.processEvents()

        try:
            writer = PdfWriter()
            reader = PdfReader(self.file_path)
            
            for item in items:
                if item.get('marked'):
                    continue
                
                page = reader.pages[item['page']]
                if item['rotation'] != 0:
                    page.rotate(item['rotation'])
                writer.add_page(page)

            output_name = f"edited_{os.path.basename(self.file_path)}"
            output_path = os.path.join(get_downloads_folder(), output_name)
            
            with open(output_path, "wb") as f:
                writer.write(f)

            QMessageBox.information(self, "Success", f"File saved successfully:\n{output_name}")
            open_file(output_path)
            self.close()

        except Exception as e:
            self.save_btn.setText("Save Changes")
            self.save_btn.setEnabled(True)
            QMessageBox.critical(self, "Error", f"Save failed: {str(e)}")
        finally:
            cleanup_temp_folder(self.temp_folder)

def main():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    TEMP_FOLDER = "page_editor_temp"
    
    # שימוש ב-get_files עם הגבלה לקובץ 1 בלבד
    files = get_files(max_files=1, target_folder=TEMP_FOLDER)
    
    if not files:
        cleanup_temp_folder(TEMP_FOLDER)
        sys.exit()

    target_file = files[0]

    # בדיקה שהקובץ הוא PDF
    if not target_file.lower().endswith(".pdf"):
        QMessageBox.critical(None, "Error", "Only PDF files allowed")
        cleanup_temp_folder(TEMP_FOLDER)
        sys.exit()

    window = DeletePagesWindow(target_file, TEMP_FOLDER)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()