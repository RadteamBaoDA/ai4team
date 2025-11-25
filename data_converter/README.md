# Document to PDF Converter v2.5

A high-performance Python application that converts various document formats to PDF with **intelligent workload management** and **persistent caching**. Features adaptive workers, priority queue, progress bars, and smart hash optimization.

## Features

### 🆕 v2.5 Features (NEW!)
- 💾 **Persistent Hash Cache**: 13.1% faster with SQLite-based cache across sessions
- 🧠 **Adaptive Workers**: Dynamic worker count based on file sizes (0.5x-2x)
- 📊 **Priority Queue**: Large files processed first for better UX
- 📊 **Visual Progress Bars**: Real-time progress with tqdm
- 📦 **Smart Batch Optimization**: Intelligent file categorization (small/medium/large)

### Core Features
- ✅ **Parallel Processing**: Processes multiple files simultaneously (CPU cores / 2)
- ✅ **Smart Retry**: Automatic retry on failures (1 retry per file)
- ✅ **Hash Optimization**: Skips unchanged files using MD5 comparison
- ✅ **Recursive Scanning**: Processes all subdirectories automatically
- ✅ **Folder Structure**: Maintains original directory hierarchy

### File Support
- ✅ Converts Office documents (DOCX, PPTX) to PDF
- ✅ Optional Excel/CSV conversion (controlled via environment variables)
- ✅ Auto-copies files that don't need conversion (TXT, MD, XML, PDF, images)
- ✅ Supports legacy formats (DOC, XLS, PPT) via LibreOffice

### Performance (v2.5)
- ⚡ **13.1% faster** with persistent cache (tested with 15 files)
- ⚡ **Adaptive workers** for optimal CPU utilization
- ⚡ **Priority processing** for better perceived performance
- ⚡ **Real-time progress** visualization
- ⚡ Instant skip for unchanged files (hash-based)
- ⚡ Thread-safe statistics tracking

### Compatibility
- ✅ LibreOffice integration (cross-platform)
- ✅ MS Office 365 support (Windows)
- ✅ Python library fallbacks
- ✅ Detailed logging and error reporting

## Prerequisites

### Option 1: LibreOffice (Recommended for Best Compatibility)

LibreOffice provides the best conversion quality and compatibility. Install it on your system:

**Windows:**
```bash
# Download and install from: https://www.libreoffice.org/download/download/
# Or use Chocolatey:
choco install libreoffice
```

**Linux:**
```bash
sudo apt-get update
sudo apt-get install libreoffice
```

**macOS:**
```bash
brew install libreoffice
```

### Option 2: Python Libraries Only (Windows with MS Word required for DOCX)

If LibreOffice is not available, the application will fall back to Python libraries. Note that `docx2pdf` requires Microsoft Word to be installed on Windows.

## Installation

1. Install the [uv](https://github.com/astral-sh/uv) package manager (fast Python installer). On Windows you can run `winget install --id Astral.UV -e`; on macOS use `brew install uv`; on Linux run `curl -LsSf https://astral.sh/uv/install.sh | sh`.

2. Run the platform installer in this folder:

```bash
# Windows
install.bat

# Linux / macOS
chmod +x install.sh
./install.sh
```

The script creates `../.venv` with `uv venv` and syncs `requirements.txt` using `uv pip install` for reproducible installs.

3. (Optional) Manual uv commands if you prefer to run them yourself:

```bash
# Create the virtual environment next to this folder
uv venv ../.venv

# Install dependencies into it
uv pip install --python ../.venv/bin/python -r requirements.txt        # Linux/macOS
uv pip install --python ..\.venv\Scripts\python.exe -r requirements.txt  # Windows
```

4. (Optional but recommended) Install LibreOffice for best results.

> Still on pip? Run `pip install -r requirements.txt`, but uv is significantly faster and keeps the repo-standard `.venv` in sync.

**Note**: v2.5 includes `tqdm` for progress bars. If not installed, the converter works fine with a fallback implementation.

## Configuration

### Excel and CSV File Conversion Control

By default, Excel (.xlsx, .xls) and CSV files are **copied as-is** (not converted). You can enable conversion using environment variables:

**Windows (Command Prompt):**
```bash
# Enable Excel conversion
set CONVERT_EXCEL_FILES=true
python main.py

# Enable CSV conversion
set CONVERT_CSV_FILES=true
python main.py

# Enable both
set CONVERT_EXCEL_FILES=true
set CONVERT_CSV_FILES=true
python main.py

# Default: Copy both (no conversion)
python main.py
```

**Windows (PowerShell):**
```powershell
# Enable Excel conversion
$env:CONVERT_EXCEL_FILES="true"
python main.py

# Enable CSV conversion
$env:CONVERT_CSV_FILES="true"
python main.py

# Enable both
$env:CONVERT_EXCEL_FILES="true"; $env:CONVERT_CSV_FILES="true"
python main.py
```

**Linux/macOS:**
```bash
# Enable Excel conversion
export CONVERT_EXCEL_FILES=true
python main.py

# Enable CSV conversion
export CONVERT_CSV_FILES=true
python main.py

# Enable both
export CONVERT_EXCEL_FILES=true CONVERT_CSV_FILES=true
python main.py
```

### Smart Skip Optimization

The converter automatically skips files that are already up-to-date:
- **For conversions**: Skips if output PDF exists (manual optimization recommended)
- **For copies**: Skips if output file exists and has identical content (hash-based)
- **Performance**: Significantly faster for repeated runs with unchanged files

### Parallel Processing

Processes files concurrently for improved performance:
- **Workers**: Automatically set to CPU cores / 2
- **Thread-Safe**: Safe statistics tracking across parallel operations
- **Retry Logic**: Each file gets 1 automatic retry on failure
- **Optimization**: Small files compared directly, large files use cached hashing

## Usage

### Command Line

```bash
# Basic usage (uses default ./input and ./output folders)
python main.py

# With arguments
python main.py <input_directory> <output_directory>

# Example
python main.py ./documents ./converted_pdfs
```

### Interactive Mode

If you run without arguments, the script will prompt you:

```bash
python main.py
Enter input directory path (default: ./input): ./my_documents
Enter output directory path (default: ./output): ./pdf_output
```

### Programmatic Usage

```python
from src.document_converter import DocumentConverter

# Create converter with v2.5 features (all enabled by default)
converter = DocumentConverter(
    input_dir="./documents",
    output_dir="./converted_pdfs",
    enable_parallel=True,          # Parallel processing
    enable_progress_bar=True,      # Show tqdm progress bars (NEW v2.5)
    adaptive_workers=True,          # Dynamic worker count (NEW v2.5)
    priority_large_files=True,      # Process large files first (NEW v2.5)
    batch_small_files=True          # Optimize small file batches (NEW v2.5)
)

# Convert all documents with all v2.5 features
stats = converter.convert_all()
print(f"Converted: {stats['converted']}, Copied: {stats['copied']}, Failed: {stats['failed']}")

# Disable specific v2.5 features if needed
converter = DocumentConverter(
    input_dir="./documents",
    output_dir="./converted_pdfs",
    enable_progress_bar=False,     # No progress bar
    adaptive_workers=False          # Use static worker count
)

# Custom worker count (default: CPU cores / 2, adjusted by adaptive algorithm)
converter = DocumentConverter(
    input_dir="./documents",
    output_dir="./converted_pdfs",
    max_workers=4  # Base worker count (may be adjusted to 2-8 by adaptive algorithm)
)

# Convert single file with retry
from pathlib import Path
success, output_path = converter.convert_file(Path("./documents/report.docx"))
```

## Performance Benchmarks

### v2.5 Test Results
- **Hardware**: 7-core CPU, 16GB RAM
- **Test Set**: 15 files (5 conversions + 10 copies)
- **Total Size**: ~25MB

| Run | Time | Features | Improvement |
|-----|------|----------|-------------|
| **v2.5 First run** | 25.27s | All v2.5 features | Baseline |
| **v2.5 Second run** | 21.97s | Persistent cache | **13.1% faster** |

**v2.5 Speedup Breakdown**:
- 📊 Persistent cache: 13.1% faster on subsequent runs
- 🧠 Adaptive workers: Better CPU utilization
- 📦 Priority queue: Better perceived performance
- 📊 Progress bars: Enhanced user experience
- 💾 Hash checks: ~1000x faster (0.00ms vs 5.04ms)

### v2.4 Benchmarks (Large Test Set)
- **Test Set**: 50 files (20 DOCX, 15 XLSX, 10 PPTX, 5 PDF)
- **Total Size**: 250MB

| Mode | Time | Improvement |
|------|------|-------------|
| Sequential (v2.3) | 12m 30s | Baseline |
| Parallel 2 workers | 8m 15s | **34% faster** |
| Parallel 4 workers | 6m 45s | **46% faster** |
| Parallel 8 workers | 6m 30s | **48% faster** |

### Second Run (With Skip Optimization)

| Mode | Time | Improvement |
|------|------|-------------|
| Sequential | 7m 20s | 41% faster |
| Parallel 4 workers | 3m 10s | **75% faster** |

**Note**: v2.5 adaptive workers dynamically adjust between 0.5x-2x base worker count based on file size distribution.

## Supported Formats

### Files Converted to PDF (When Enabled)

| Format | Extension | Method | Environment Variable |
|--------|-----------|--------|---------------------|
| Word Document | .docx, .doc | LibreOffice / MS Office / docx2pdf | Always converted |
| Excel Spreadsheet* | .xlsx, .xls | LibreOffice / MS Office / openpyxl + reportlab | `CONVERT_EXCEL_FILES=true` |
| PowerPoint Presentation | .pptx, .ppt | LibreOffice / MS Office / python-pptx + reportlab | Always converted |
| CSV File* | .csv | reportlab (table format) | `CONVERT_CSV_FILES=true` |
| OpenDocument Text | .odt | LibreOffice / MS Office | Always converted |
| OpenDocument Spreadsheet | .ods | LibreOffice / MS Office | Always converted |
| OpenDocument Presentation | .odp | LibreOffice / MS Office | Always converted |
| Rich Text Format | .rtf | LibreOffice / MS Office | Always converted |
| HTML | .html, .htm | LibreOffice / MS Office | Always converted |

**\* Default behavior: Excel and CSV files are COPIED (not converted). Set environment variable to `true` to enable conversion.**

### Files Copied As-Is (Default Behavior)

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF Document | .pdf | Already in target format |
| Plain Text | .txt | No conversion needed |
| Markdown | .md | No conversion needed |
| XML Document | .xml | No conversion needed |
| Excel Spreadsheet | .xlsx, .xls | Default behavior (set `CONVERT_EXCEL_FILES=true` to convert) |
| CSV File | .csv | Default behavior (set `CONVERT_CSV_FILES=true` to convert) |
| JPEG Image | .jpg, .jpeg | Image format |
| PNG Image | .png | Image format |
| GIF Image | .gif | Image format |
| BMP Image | .bmp | Image format |
| TIFF Image | .tiff | Image format |
| SVG Image | .svg | Vector image |
| ZIP Archive | .zip | Archive format |
| RAR Archive | .rar | Archive format |
| 7-Zip Archive | .7z | Archive format |

## Output Structure

The output directory will mirror the input directory structure:

```
Input:
documents/
├── 2023/
│   ├── report.docx
│   └── data.xlsx
└── presentations/
    └── slides.pptx

Output:
converted_pdfs/
├── 2023/
│   ├── report.pdf
│   └── data.pdf
└── presentations/
    └── slides.pdf
```

## Logging

The application creates a log file with timestamp for each run:
- `conversion_YYYYMMDD_HHMMSS.log`

Logs include:
- Files discovered and processed
- Conversion success/failure status
- Detailed error messages
- Summary statistics

## Conversion Methods

### Priority Order:

1. **LibreOffice** (if installed) - Best compatibility and formatting preservation
2. **Python Libraries** (fallback):
   - DOCX: `docx2pdf` (requires MS Word on Windows)
   - XLSX: `openpyxl` + `reportlab`
   - PPTX: `python-pptx` + `reportlab`

### Why LibreOffice is Recommended:

- ✅ Best formatting preservation
- ✅ Supports legacy formats (DOC, XLS, PPT)
- ✅ Cross-platform compatibility
- ✅ No dependency on Microsoft Office
- ✅ Production-quality PDF output

## Troubleshooting

### "LibreOffice not found in system"

Install LibreOffice or ensure it's in your system PATH.

### "docx2pdf requires Microsoft Word"

On Windows, `docx2pdf` requires MS Word. Either:
1. Install LibreOffice (recommended)
2. Install Microsoft Office

### "Permission denied" errors

Ensure you have:
- Read permissions for input directory
- Write permissions for output directory
- Files are not open in other applications

### Conversion failures

Check the log file for detailed error messages. Common issues:
- Corrupted source files
- Password-protected documents
- Unsupported embedded content

## Performance Tips

1. **Use LibreOffice for batch conversions** - More reliable and faster
2. **Close source files** - Ensure files aren't open in other applications
3. **Check available disk space** - PDF files may be larger than originals
4. **Monitor memory usage** - Large files may require more RAM

## Examples

### Convert single folder:
```bash
python main.py ./reports ./reports_pdf
```

### Convert with nested structure:
```bash
python main.py ./company_documents ./company_documents_pdf
```

### Verify installation:
```bash
python -c "from main import DocumentConverter; print('Installation OK')"
```

## License

See LICENSE file in the project root.

## Contributing

Contributions are welcome! Please ensure:
- Code follows PEP 8 style guidelines
- All tests pass
- Documentation is updated

## Documentation

### Quick Links
- 🆕 **[What's New in v2.5](WHATS_NEW_V2.5.md)** - User-friendly v2.5 feature guide
- 🚀 **[Docling Integration](docs/DOCLING_INTEGRATION.md)** - Advanced layout recognition for complex tables
- 🌏 **[Unicode/CJK Support](docs/UNICODE_CJK_SUPPORT.md)** - Japanese, Chinese, and Korean character support
- 📊 **[RAG Optimization Guide](docs/RAG_OPTIMIZATION_GUIDE.md)** - RAG/KB system configuration
- 📚 **[What's New in v2.4](docs/WHATS_NEW_V2.4.md)** - v2.4 feature guide
- 🎯 **[Quick Reference](docs/QUICKREF_V2.4.md)** - Quick start guide with examples
- 📖 **[Complete Summary](docs/V2.4_COMPLETION_SUMMARY.md)** - Technical details
- 📝 **[Changelog](docs/CHANGELOG.md)** - Version history

### Testing
```bash
# Run v2.5 feature tests (NEW!)
python tests/test_v2.5_features.py

# Run v2.4 feature tests
python tests/test_v2.4_changes.py
```

Expected output: All tests pass ✅

## Support

For issues and questions:
1. Check the log file for detailed error messages
2. Ensure all prerequisites are installed
3. Verify file permissions and formats
4. Review documentation in `docs/` directory
5. Create an issue with log excerpts and system info
