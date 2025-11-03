#!/usr/bin/env python3
"""
Test new converters and copy functionality
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.document_converter import DocumentConverter
from config import settings


def test_supported_extensions():
    """Test supported extensions"""
    print("=" * 70)
    print("SUPPORTED FILE TYPES")
    print("=" * 70)
    print()
    
    print("Convertible to PDF:")
    for ext in sorted(settings.CONVERTIBLE_EXTENSIONS):
        print(f"  {ext}")
    
    print(f"\nTotal: {len(settings.CONVERTIBLE_EXTENSIONS)} types")
    
    print("\n" + "-" * 70)
    print("\nCopy as-is (no conversion):")
    for ext in sorted(settings.COPY_EXTENSIONS):
        print(f"  {ext}")
    
    print(f"\nTotal: {len(settings.COPY_EXTENSIONS)} types")
    print()


def test_file_detection():
    """Test file detection and categorization"""
    print("=" * 70)
    print("FILE DETECTION TEST")
    print("=" * 70)
    print()
    
    converter = DocumentConverter()
    
    # Find files
    files_to_convert, files_to_copy = converter.scanner.categorize_files()
    
    print(f"Files to convert: {len(files_to_convert)}")
    for f in files_to_convert[:10]:  # Show first 10
        print(f"  {f.suffix}: {f.name}")
    if len(files_to_convert) > 10:
        print(f"  ... and {len(files_to_convert) - 10} more")
    
    print(f"\nFiles to copy: {len(files_to_copy)}")
    for f in files_to_copy[:10]:  # Show first 10
        print(f"  {f.suffix}: {f.name}")
    if len(files_to_copy) > 10:
        print(f"  ... and {len(files_to_copy) - 10} more")
    
    print()


def test_csv_converter():
    """Test CSV converter specifically"""
    print("=" * 70)
    print("CSV CONVERTER TEST")
    print("=" * 70)
    print()
    
    from src.converters import CsvConverter
    
    converter = CsvConverter()
    print(f"CSV Converter available: {converter.is_available()}")
    print()


def main():
    """Run all tests"""
    print("\n")
    print("*" * 70)
    print("DOCUMENT CONVERTER v2.1 - NEW FEATURES TEST")
    print("*" * 70)
    print("\n")
    
    test_supported_extensions()
    test_file_detection()
    test_csv_converter()
    
    print("=" * 70)
    print("TESTS COMPLETE")
    print("=" * 70)
    print()
    print("New features:")
    print("  ✓ CSV file support")
    print("  ✓ Text file support (.txt, .md, .rtf, .xml)")
    print("  ✓ HTML file support")
    print("  ✓ OpenDocument support (.odt, .ods, .odp)")
    print("  ✓ Auto-copy for PDFs and images")
    print()


if __name__ == "__main__":
    main()
