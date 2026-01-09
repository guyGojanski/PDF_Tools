# 📄 PDF Master Suite

## 🛠️ Features

- **📋 Merge PDF**: Combine multiple PDF documents into a single organized file with support for encrypted PDFs
- **✂️ Split PDF**: Divide PDFs using three flexible modes:
  - Range Mode: Define custom page ranges
  - Pages Mode: Extract specific pages
  - Size Mode: Split by file size (auto-optimized)
- **🗑️ Delete Pages**: Remove specific pages from any PDF with live preview and parity selection (odd/even)

---

## 📁 Project Structure

```
PDF.py                          # Main application entry point
assets/
├── config.py                  # Global configuration constants
├── styles.qss                 # QSS stylesheet for UI theming
└── ico/                       # Icon assets
component/
├── toolsForPDF.py             # Shared PDF utilities & helpers
├── file_picker.py             # File selection dialog
├── file_card.py               # PDF file card widget
├── pdf_grid.py                # Grid layout for PDF cards
├── header_bar.py              # Header navigation bar
└── __init__.py
modules/
├── MergePDF.py                # Merge functionality
├── SplitPDF.py                # Split functionality with range/pages/size modes
├── DeletePages.py             # Page deletion functionality
└── __init__.py
tests/
├── test_pdf_app.py            # Unit tests
└── run_tests.py               # Test runner with coverage
requirements.txt               # Project dependencies
ReadME.md                       # This file
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **pip** (Python package manager)

### Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/guyGojanski/PDF_Tools.git
   cd PDF_Tools
   ```

2. **Create a virtual environment** (recommended):

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

```bash
python PDF.py
```

---

## 📦 Dependencies

- **PyQt6**: GUI framework
- **pypdf**: PDF manipulation library
- **PyMuPDF (fitz)**: PDF preview and thumbnail generation
- **Pillow**: Image processing

See `requirements.txt` for complete list with versions.

---

## 🧪 Testing

Run the test suite with coverage:

```bash
python tests/run_tests.py
```

Tests include:

- PDF validation and encryption detection
- Page range parsing and formatting
- File collision handling
- Filename truncation
- Rotation calculations
- PDF cleanup resilience

---

## 📄 License

This project is open-source and available for personal, educational, or commercial use. Feel free to fork, modify, and contribute!

**Developed by Guy Gojanski**
