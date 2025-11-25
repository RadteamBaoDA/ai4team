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

# Excel Page Break Configuration
# Number of consecutive empty rows to trigger a page break (0 to disable)
EXCEL_PAGE_BREAK_ON_EMPTY_ROWS = _env_int('EXCEL_PAGE_BREAK_ON_EMPTY_ROWS', 1)
# Special character/string to trigger a page break (empty string to disable)
EXCEL_PAGE_BREAK_CHAR = os.getenv('EXCEL_PAGE_BREAK_CHAR', '<<<PAGE_BREAK>>>')

# Excel RAG Optimization Settings (only applies when RAG_OPTIMIZATION_ENABLED=True)
# Print row and column headers (A, B, C... and 1, 2, 3...) for better cell referencing
EXCEL_PRINT_ROW_COL_HEADERS = _env_bool('EXCEL_PRINT_ROW_COL_HEADERS', True)  # Note: Also controlled by RAG_OPTIMIZATION_ENABLED in converter
# Print gridlines for better table structure recognition
EXCEL_PRINT_GRIDLINES = _env_bool('EXCEL_PRINT_GRIDLINES', True)  # Note: Also controlled by RAG_OPTIMIZATION_ENABLED in converter
# Print in black and white (better OCR, smaller file size)
EXCEL_BLACK_AND_WHITE = _env_bool('EXCEL_BLACK_AND_WHITE', False)
# Add sheet name and page info to header/footer
EXCEL_ADD_CITATION_HEADERS = _env_bool('EXCEL_ADD_CITATION_HEADERS', True)  # Note: Also controlled by RAG_OPTIMIZATION_ENABLED in converter

# Table optimization: Maximum rows per page when content is detected as a table
# This helps RAG systems parse tables more accurately by limiting table size per page
# Set to 0 to disable automatic table page breaks
EXCEL_TABLE_MAX_ROWS_PER_PAGE = _env_int('EXCEL_TABLE_MAX_ROWS_PER_PAGE', 15)
# Enable table detection and optimization
EXCEL_TABLE_OPTIMIZATION = _env_bool('EXCEL_TABLE_OPTIMIZATION', True)

# =============================================================================
# Advanced Layout Recognition Settings (Docling)
# =============================================================================

# Enable Docling converter for enhanced layout recognition
# Requires: pip install docling
# Best for: Complex Excel tables, multi-sheet workbooks, advanced layout analysis
USE_DOCLING_CONVERTER = _env_bool('USE_DOCLING_CONVERTER', False)
# Docling converter priority (higher = try earlier)
# 0=disabled, 1=fallback only, 2=before Python converters, 3=before LibreOffice, 4=before MS Office
DOCLING_PRIORITY = _env_int('DOCLING_PRIORITY', 4)

# Docling API Settings (docling-serve)
# Enable using remote Docling API instead of local processing
DOCLING_API_ENABLED = _env_bool('DOCLING_API_ENABLED', False)
# URL of the Docling API server (e.g., http://localhost:8000)
DOCLING_API_URL = os.getenv('DOCLING_API_URL', 'http://localhost:8000')
# Timeout for API requests in seconds
DOCLING_API_TIMEOUT = _env_int('DOCLING_API_TIMEOUT', 120)

# =============================================================================
# RAG & Knowledge Base Optimization Settings
# =============================================================================

# Master toggle to enable/disable ALL RAG optimizations added in this session
# Set to False to use standard PDF export without RAG-specific features
RAG_OPTIMIZATION_ENABLED = _env_bool('RAG_OPTIMIZATION_ENABLED', True)

# PDF Structure for better parsing (only applies when RAG_OPTIMIZATION_ENABLED=True)
PDF_CREATE_BOOKMARKS = RAG_OPTIMIZATION_ENABLED and _env_bool('PDF_CREATE_BOOKMARKS', True)  # Create PDF outline from headings
PDF_CREATE_TAGGED = RAG_OPTIMIZATION_ENABLED and _env_bool('PDF_CREATE_TAGGED', True)  # Create tagged PDF for accessibility & structure
PDF_EMBED_FONTS = RAG_OPTIMIZATION_ENABLED and _env_bool('PDF_EMBED_FONTS', True)  # Embed all fonts for consistent rendering
PDF_USE_ISO19005 = RAG_OPTIMIZATION_ENABLED and _env_bool('PDF_USE_ISO19005', True)  # PDF/A compliance for archival

# Word RAG Settings (only applies when RAG_OPTIMIZATION_ENABLED=True)
WORD_CREATE_HEADING_BOOKMARKS = RAG_OPTIMIZATION_ENABLED and _env_bool('WORD_CREATE_HEADING_BOOKMARKS', True)
WORD_ADD_DOC_PROPERTIES = RAG_OPTIMIZATION_ENABLED and _env_bool('WORD_ADD_DOC_PROPERTIES', True)
WORD_PRESERVE_STRUCTURE_TAGS = RAG_OPTIMIZATION_ENABLED and _env_bool('WORD_PRESERVE_STRUCTURE_TAGS', True)

# PowerPoint RAG Settings (only applies when RAG_OPTIMIZATION_ENABLED=True)
PPTX_ADD_SLIDE_NUMBERS = RAG_OPTIMIZATION_ENABLED and _env_bool('PPTX_ADD_SLIDE_NUMBERS', True)
PPTX_CREATE_OUTLINE = RAG_OPTIMIZATION_ENABLED and _env_bool('PPTX_CREATE_OUTLINE', True)  # Create bookmarks from slide titles
PPTX_NOTES_AS_TEXT = RAG_OPTIMIZATION_ENABLED and _env_bool('PPTX_NOTES_AS_TEXT', False)  # Include speaker notes
PPTX_ADD_DOC_PROPERTIES = RAG_OPTIMIZATION_ENABLED and _env_bool('PPTX_ADD_DOC_PROPERTIES', True)

# Citation Format Settings (only applies when RAG_OPTIMIZATION_ENABLED=True)
CITATION_INCLUDE_FILENAME = RAG_OPTIMIZATION_ENABLED and _env_bool('CITATION_INCLUDE_FILENAME', True)
CITATION_INCLUDE_DATE = RAG_OPTIMIZATION_ENABLED and _env_bool('CITATION_INCLUDE_DATE', True)
CITATION_INCLUDE_PAGE = RAG_OPTIMIZATION_ENABLED and _env_bool('CITATION_INCLUDE_PAGE', True)
CITATION_DATE_FORMAT = os.getenv('CITATION_DATE_FORMAT', '%Y-%m-%d')

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
