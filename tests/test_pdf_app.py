import unittest
import os
import shutil
from unittest.mock import patch
from pypdf import PdfWriter
from PyQt6.QtWidgets import QApplication
import sys

# ייבוא הפונקציות
from component.toolsForPDF import (
    is_valid_pdf,
    is_pdf_encrypted,
    safe_copy_file,
    get_pdf_thumbnail,
    validate_only_pdfs,
    attempt_pdf_decryption,
    cleanup_temp_folder
)

class TestPDFToolsStrict(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # אתחול אפליקציית Qt לבדיקות גרפיות
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

        cls.test_dir = "test_env_strict"
        if not os.path.exists(cls.test_dir):
            os.makedirs(cls.test_dir)

        # 1. PDF תקין
        cls.valid_pdf = os.path.join(cls.test_dir, "valid.pdf")
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        with open(cls.valid_pdf, "wb") as f:
            writer.write(f)

        # 2. PDF מוצפן (סיסמה: 1234)
        cls.locked_pdf = os.path.join(cls.test_dir, "locked.pdf")
        writer_enc = PdfWriter()
        writer_enc.add_blank_page(width=100, height=100)
        writer_enc.encrypt("1234")
        with open(cls.locked_pdf, "wb") as f:
            writer_enc.write(f)

        # 3. PDF מושחת (Corrupt) - התחלה תקינה, סוף זבל
        cls.corrupt_pdf = os.path.join(cls.test_dir, "corrupt.pdf")
        with open(cls.corrupt_pdf, "wb") as f:
            f.write(b"%PDF-1.4\n...garbage content...")

        # 4. קובץ ריק לחלוטין
        cls.empty_file = os.path.join(cls.test_dir, "empty.pdf")
        with open(cls.empty_file, "w") as f:
            pass

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            try:
                shutil.rmtree(cls.test_dir)
            except Exception:
                pass

    # --- בדיקות הצפנה ופענוח (החלק הקשוח) ---

    def test_decrypt_success(self):
        """בדיקה שהפענוח מצליח עם הסיסמה הנכונה ויוצר קובץ חדש"""
        decrypted_path = attempt_pdf_decryption(self.locked_pdf, "1234", self.test_dir)
        self.assertIsNotNone(decrypted_path)
        self.assertTrue(os.path.exists(decrypted_path))
        self.assertFalse(is_pdf_encrypted(decrypted_path)) # הקובץ החדש צריך להיות פתוח

    def test_decrypt_wrong_password(self):
        """בדיקה שהפענוח נכשל עם סיסמה שגויה ומחזיר None"""
        result = attempt_pdf_decryption(self.locked_pdf, "wrongpass", self.test_dir)
        self.assertIsNone(result)

    def test_is_pdf_encrypted_detection(self):
        self.assertTrue(is_pdf_encrypted(self.locked_pdf))
        self.assertFalse(is_pdf_encrypted(self.valid_pdf))

    # --- בדיקות תקינות קבצים (Edge Cases) ---

    def test_validity_checks(self):
        # קובץ תקין
        self.assertTrue(is_valid_pdf(self.valid_pdf))
        
        # קובץ ריק - חייב להיכשל
        self.assertFalse(is_valid_pdf(self.empty_file))
        
        # קובץ מושחת - חייב להיכשל (fitz יזרוק שגיאה פנימית והפונקציה תחזיר False)
        self.assertFalse(is_valid_pdf(self.corrupt_pdf))

    # --- בדיקות מערכת קבצים ושגיאות ---

    def test_safe_copy_integrity(self):
        """בדיקה שהעתקה שומרת על שלמות הקובץ"""
        dest_folder = os.path.join(self.test_dir, "copies")
        new_path = safe_copy_file(self.valid_pdf, dest_folder)
        
        # וידוא שגודל הקובץ זהה
        self.assertEqual(os.path.getsize(self.valid_pdf), os.path.getsize(new_path))

    @patch('shutil.copy2')
    def test_safe_copy_permission_error(self, mock_copy):
        """סימולציה של שגיאת הרשאות (Permission Denied)"""
        # אנו גורמים לפונקציית ההעתקה של פייתון לזרוק שגיאה בכוונה
        mock_copy.side_effect = PermissionError("Access denied")
        
        with self.assertRaises(OSError):
            safe_copy_file(self.valid_pdf, self.test_dir)

    def test_cleanup_folder(self):
        """בדיקה שהתיקייה הזמנית באמת נמחקת"""
        temp_cleanup = os.path.join(self.test_dir, "to_delete")
        os.makedirs(temp_cleanup)
        with open(os.path.join(temp_cleanup, "junk.txt"), "w") as f:
            f.write("junk")
            
        self.assertTrue(os.path.exists(temp_cleanup))
        cleanup_temp_folder(temp_cleanup)
        self.assertFalse(os.path.exists(temp_cleanup))

    # --- בדיקות ויזואליות ---

    def test_thumbnail_generation_strict(self):
        # קובץ תקין - חייב להחזיר תמונה
        self.assertIsNotNone(get_pdf_thumbnail(self.valid_pdf))
        
        # קובץ נעול - אסור להחזיר תמונה (אמור להחזיר None)
        self.assertIsNone(get_pdf_thumbnail(self.locked_pdf))
        
        # קובץ מושחת - אסור לקרוס, צריך להחזיר None
        self.assertIsNone(get_pdf_thumbnail(self.corrupt_pdf))

if __name__ == '__main__':
    # verbosity=2 נותן פלט מפורט יותר בטרמינל
    unittest.main(verbosity=2)