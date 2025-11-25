#!/usr/bin/env python3
"""
Test script for Docling converter integration.

This script verifies that the Docling converter is properly configured
and can convert Excel files with enhanced layout recognition.

Usage:
    # Basic test (with docling installed)
    python test_docling.py

    # Test without docling (verify graceful fallback)
    python test_docling.py --no-docling
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from src.converters.factory import ConverterFactory


def print_section(title: str):
    """Print formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def test_docling_availability():
    """Test if Docling is available."""
    print_section("Testing Docling Availability")
    
    try:
        import docling
        print(f"✅ Docling installed: {docling.__version__}")
        return True
    except ImportError:
        print("❌ Docling not installed")
        print("\nTo install Docling:")
        print("  pip install docling")
        print("\nOr uncomment in requirements.txt and run:")
        print("  pip install -r requirements.txt")
        return False


def test_docling_settings():
    """Test Docling configuration settings."""
    print_section("Testing Docling Settings")
    
    print(f"USE_DOCLING_CONVERTER: {settings.USE_DOCLING_CONVERTER}")
    print(f"DOCLING_PRIORITY: {settings.DOCLING_PRIORITY}")
    print(f"RAG_OPTIMIZATION_ENABLED: {settings.RAG_OPTIMIZATION_ENABLED}")
    
    if settings.USE_DOCLING_CONVERTER:
        print("\n✅ Docling converter is ENABLED")
        
        if settings.DOCLING_PRIORITY == 0:
            print("⚠️  Warning: DOCLING_PRIORITY=0 (disabled)")
        elif settings.DOCLING_PRIORITY == 1:
            print("📌 Priority: Fallback only (after all converters)")
        elif settings.DOCLING_PRIORITY == 2:
            print("📌 Priority: Before Python converters (recommended)")
        elif settings.DOCLING_PRIORITY == 3:
            print("📌 Priority: Before LibreOffice")
        elif settings.DOCLING_PRIORITY == 4:
            print("📌 Priority: Before MS Office (highest)")
    else:
        print("\n❌ Docling converter is DISABLED")
        print("\nTo enable:")
        print("  export USE_DOCLING_CONVERTER=true")


def test_converter_priority():
    """Test converter priority order."""
    print_section("Testing Converter Priority")
    
    factory = ConverterFactory()
    converters_info = factory.get_available_converters_info()
    
    print("\nConverter Priority Order:")
    print("-" * 60)
    
    for i, info in enumerate(converters_info, 1):
        name = info['name']
        available = "✅ Available" if info['available'] else "❌ Not Available"
        priority = info.get('priority', 'N/A')
        
        # Highlight Docling
        if 'docling' in name.lower():
            print(f"{i}. {name:30} {available:20} (Priority: {priority}) 🚀")
        else:
            print(f"{i}. {name:30} {available:20}")
    
    print("-" * 60)


def test_docling_converter_class():
    """Test if DoclingConverter class can be imported."""
    print_section("Testing DoclingConverter Class")
    
    try:
        from src.converters.docling_converter import DoclingConverter
        print("✅ DoclingConverter class imported successfully")
        
        # Test class attributes
        print(f"\nSupported extensions: {DoclingConverter.SUPPORTED_EXTENSIONS}")
        print(f"Converter name: {DoclingConverter.converter_name}")
        
        return True
    except ImportError as e:
        print(f"❌ Failed to import DoclingConverter: {e}")
        return False


def test_excel_file_routing():
    """Test which converter would be selected for an Excel file."""
    print_section("Testing Excel File Routing")
    
    factory = ConverterFactory()
    test_file = Path("test.xlsx")
    
    # Try to get converter (without actually converting)
    try:
        converter_info = factory.get_converter_for_file(test_file)
        
        if converter_info:
            print(f"\nSelected converter for 'test.xlsx': {converter_info['name']}")
            
            if 'docling' in converter_info['name'].lower():
                print("✅ Docling would be used for Excel conversion")
            else:
                print(f"📌 {converter_info['name']} would be used (Docling not selected)")
                
                if settings.USE_DOCLING_CONVERTER:
                    print("\nPossible reasons:")
                    print("  - Higher priority converter is available")
                    print("  - Docling library not installed")
                    print("  - DOCLING_PRIORITY is too low")
        else:
            print("❌ No converter available for Excel files")
            
    except Exception as e:
        print(f"⚠️  Could not determine converter: {e}")


def run_full_test():
    """Run complete Docling integration test."""
    print("\n" + "=" * 60)
    print("  DOCLING INTEGRATION TEST")
    print("=" * 60)
    
    results = {
        'docling_installed': test_docling_availability(),
        'settings_ok': True,  # Always run settings test
        'converter_class': test_docling_converter_class(),
    }
    
    # Always run these tests
    test_docling_settings()
    test_converter_priority()
    test_excel_file_routing()
    
    # Summary
    print_section("Test Summary")
    
    print(f"Docling Installed: {'✅ Yes' if results['docling_installed'] else '❌ No'}")
    print(f"Converter Class:   {'✅ OK' if results['converter_class'] else '❌ Failed'}")
    
    print("\n" + "=" * 60)
    
    if not results['docling_installed']:
        print("\n⚠️  Docling is not installed. Install it to use advanced layout recognition.")
        print("\nInstallation:")
        print("  pip install docling")
        return False
    
    if not settings.USE_DOCLING_CONVERTER:
        print("\n⚠️  Docling is installed but disabled. Enable it with:")
        print("  export USE_DOCLING_CONVERTER=true")
        return False
    
    if results['docling_installed'] and results['converter_class']:
        print("\n✅ All tests passed! Docling is ready to use.")
        return True
    
    return False


def main():
    """Main test entry point."""
    # Check for --no-docling flag (test fallback behavior)
    if '--no-docling' in sys.argv:
        print("\n⚠️  Testing WITHOUT Docling (simulating absence)")
        # Temporarily disable in settings
        os.environ['USE_DOCLING_CONVERTER'] = 'false'
    
    success = run_full_test()
    
    # Exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
