# Quick Start Guide

## Installation

### Windows:
```bash
# Run the installation script (recommended)
install.bat

# Or manually with uv
uv venv ..\.venv
uv pip install --python ..\.venv\Scripts\python.exe -r requirements.txt
```

### Linux/macOS:
```bash
# Run the installation script (recommended)
chmod +x install.sh
./install.sh

# Or manually with uv
uv venv ../.venv
uv pip install --python ../.venv/bin/python -r requirements.txt
```

## Basic Usage

### 1. Simple Conversion (Default folders)
```bash
# Uses ./input and ./output folders by default
python main.py
```

This will:
- Scan `./input` and all subdirectories
- Convert supported files to PDF
- Copy files that don't need conversion
- Save results in `./output` with same folder structure

### 2. Custom Directories
```bash
python main.py ./my_documents ./converted_pdfs
```

### 3. Control Excel and CSV Conversion

**Default behavior: Copy Excel and CSV files (no conversion):**
```bash
python main.py
```

**Convert Excel and CSV files to PDF:**

Windows (Command Prompt):
```bash
set CONVERT_EXCEL_FILES=true
set CONVERT_CSV_FILES=true
python main.py
```

Windows (PowerShell):
```powershell
$env:CONVERT_EXCEL_FILES="true"
$env:CONVERT_CSV_FILES="true"
python main.py
```

Linux/macOS:
```bash
export CONVERT_EXCEL_FILES=true
export CONVERT_CSV_FILES=true
python main.py
```

### 4. Smart Skip Feature

The converter automatically skips files that haven't changed:
- Copies are skipped if the file already exists with identical content
- Conversions can be skipped if output exists (saves time on re-runs)

## Quick Examples

### Convert company documents:
```bash
python main.py "C:\Company\Documents" "C:\Company\PDFs"
```

### Convert with default output:
```bash
python main.py ./reports ./output
```

### Convert on Linux:
```bash
python3 main.py ~/Documents/work ~/Documents/work_pdf
```

## Tips for Best Results

1. **Install LibreOffice** (highly recommended):
   - Windows: Download from https://www.libreoffice.org/
   - Linux: `sudo apt-get install libreoffice`
   - macOS: `brew install libreoffice`

2. **Close all documents** before conversion

3. **Check the log file** if conversions fail:
   - Look for `conversion_*.log` in the current directory

4. **Ensure write permissions** for output directory

## Supported Files

### Converted to PDF (When Enabled):
✅ Word: `.docx`, `.doc` (always converted)
✅ Excel: `.xlsx`, `.xls` (set `CONVERT_EXCEL_FILES=true`, default: copy)
✅ PowerPoint: `.pptx`, `.ppt` (always converted)
✅ CSV: `.csv` (set `CONVERT_CSV_FILES=true`, default: copy)
✅ OpenDocument: `.odt`, `.ods`, `.odp` (always converted)
✅ Other: `.rtf`, `.html`, `.htm` (always converted)

### Copied As-Is (Default):
✅ Documents: `.pdf`, `.txt`, `.md`, `.xml`
✅ Data: `.xlsx`, `.xls`, `.csv` (default behavior)
✅ Images: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.svg`
✅ Archives: `.zip`, `.rar`, `.7z`

## Output Structure

Input and output structures are mirrored:

```
Input:              Output:
documents/          pdfs/
  ├── 2024/           ├── 2024/
  │   └── Q1.docx     │   └── Q1.pdf
  └── slides.pptx     └── slides.pdf
```

## Troubleshooting

### "No module named 'docx2pdf'"
```bash
uv pip install -r requirements.txt
```

### "LibreOffice not found"
Either install LibreOffice or ensure it's in your system PATH.

### Permission errors
- Check folder permissions
- Close files in other applications
- Run as administrator (Windows) or use sudo (Linux) if needed

## Getting Help

1. Check `README.md` for detailed documentation
2. Review log files for error details
3. Run `python main.py --help` for options

## Next Steps

- Review the full `README.md` for advanced usage
- Check `example_usage.py` for code examples
- Customize `main.py` for your specific needs
