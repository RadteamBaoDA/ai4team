"""
Configuration settings for Document Converter
"""

import os
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    """Read environment variable as boolean with a tolerant parser."""
    return os.getenv(name, str(default)).lower() in ('true', '1', 'yes')


def _env_float(name: str, default: float) -> float:
    """Read environment variable as float with graceful fallback."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    """Read environment variable as int with graceful fallback."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default

# Base directory (where main.py is located)
BASE_DIR = Path(__file__).resolve().parent.parent

# Default directories relative to base directory
DEFAULT_INPUT_DIR = BASE_DIR / "input"
DEFAULT_OUTPUT_DIR = BASE_DIR / "output"

# Environment variables to control file conversion
# Set to "false", "0", or "no" to copy files instead of converting (default: false)
CONVERT_EXCEL_FILES = _env_bool('CONVERT_EXCEL_FILES', True)
CONVERT_CSV_FILES = _env_bool('CONVERT_CSV_FILES', False)

# Supported file extensions for conversion
CONVERTIBLE_EXTENSIONS = {
    '.docx', '.doc',      # Word documents
    '.pptx', '.ppt',      # PowerPoint presentations
    '.odt',               # OpenDocument Text
    '.ods',               # OpenDocument Spreadsheet
    '.odp',               # OpenDocument Presentation
    '.rtf',               # Rich Text Format
    '.html', '.htm',      # HTML files
}

# Excel extensions - conditionally added based on environment variable
if CONVERT_EXCEL_FILES:
    CONVERTIBLE_EXTENSIONS.update({'.xlsx', '.xls'})

# CSV extensions - conditionally added based on environment variable
if CONVERT_CSV_FILES:
    CONVERTIBLE_EXTENSIONS.add('.csv')

# File extensions to copy as-is (no conversion needed)
COPY_EXTENSIONS = {
    '.pdf',               # Already PDF
    '.txt',               # Plain text files
    '.md',                # Markdown files
    '.xml',               # XML files
    '.jpg', '.jpeg',      # Images
    '.png',
    '.gif',
    '.bmp',
    '.tiff',
    '.svg',
    '.zip',               # Archives
    '.rar',
    '.7z',
}

# Excel extensions - added to copy list if not converting
if not CONVERT_EXCEL_FILES:
    COPY_EXTENSIONS.update({'.xlsx', '.xls'})

# CSV extensions - added to copy list if not converting
if not CONVERT_CSV_FILES:
    COPY_EXTENSIONS.add('.csv')

# Combined supported extensions
SUPPORTED_EXTENSIONS = CONVERTIBLE_EXTENSIONS | COPY_EXTENSIONS

# Conversion timeout (seconds)
CONVERSION_TIMEOUT = 120

# Parallel processing configuration
PARALLEL_MODE = _env_bool('PARALLEL_MODE', False)
MAX_WORKERS = _env_int('MAX_WORKERS', None)  # None means auto-detect
BATCH_SIZE = _env_int('BATCH_SIZE', 10)
MEMORY_OPTIMIZATION = _env_bool('MEMORY_OPTIMIZATION', True)
# Use process isolation (multiprocessing) instead of threads for better memory management and stability
USE_PROCESS_ISOLATION = _env_bool('USE_PROCESS_ISOLATION', True)

# Excel PDF export tuning
EXCEL_FORCE_SINGLE_PAGE = _env_bool('EXCEL_FORCE_SINGLE_PAGE', False)
EXCEL_AUTO_LANDSCAPE = _env_bool('EXCEL_AUTO_LANDSCAPE', True)
EXCEL_LIMIT_PRINT_AREA = _env_bool('EXCEL_LIMIT_PRINT_AREA', False)
EXCEL_SINGLE_PAGE_THRESHOLD = _env_int('EXCEL_SINGLE_PAGE_THRESHOLD', 7)
EXCEL_MARGIN_INCHES = _env_float('EXCEL_MARGIN_INCHES', 0.5)
EXCEL_HEADER_MARGIN_INCHES = _env_float('EXCEL_HEADER_MARGIN_INCHES', 0.3)

# LibreOffice command paths to try
LIBREOFFICE_COMMANDS = [
    'libreoffice',
    'soffice',
    '/usr/bin/libreoffice',
    '/usr/bin/soffice',
    'C:\\Program Files\\LibreOffice\\program\\soffice.exe',
    'C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe'
]

# Microsoft Office paths
MS_OFFICE_PATHS = {
    'word': [
        'C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE',
        'C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\WINWORD.EXE',
        'C:\\Program Files\\Microsoft Office 16\\root\\Office16\\WINWORD.EXE',
    ],
    'excel': [
        'C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE',
        'C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\EXCEL.EXE',
        'C:\\Program Files\\Microsoft Office 16\\root\\Office16\\EXCEL.EXE',
    ],
    'powerpoint': [
        'C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE',
        'C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\POWERPNT.EXE',
        'C:\\Program Files\\Microsoft Office 16\\root\\Office16\\POWERPNT.EXE',
    ]
}

# Logging configuration
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
