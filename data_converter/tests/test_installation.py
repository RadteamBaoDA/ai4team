#!/usr/bin/env python3
"""
Test script to verify installation and dependencies
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test if all required packages can be imported"""
    print("Testing dependencies...\n")
    
    tests = {
        'docx2pdf': 'docx2pdf',
        'openpyxl': 'openpyxl',
        'python-pptx': 'pptx',
        'reportlab': 'reportlab'
    }
    
    failed = []
    
    for package_name, import_name in tests.items():
        try:
            __import__(import_name)
            print(f"✓ {package_name:20} OK")
        except ImportError as e:
            print(f"✗ {package_name:20} FAILED: {e}")
            failed.append(package_name)
    
    print()
    
    if failed:
        print(f"❌ {len(failed)} package(s) failed to import:")
        for pkg in failed:
            print(f"   - {pkg}")
        print("\nRun: pip install -r requirements.txt")
        return False
    else:
        print("✅ All dependencies are installed correctly!")
        return True


def test_libreoffice():
    """Test if LibreOffice is available"""
    import subprocess
    
    print("\nTesting LibreOffice availability...\n")
    
    commands = [
        'libreoffice',
        'soffice',
        'C:\\Program Files\\LibreOffice\\program\\soffice.exe',
        'C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe'
    ]
    
    for cmd in commands:
        try:
            result = subprocess.run(
                [cmd, '--version'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.decode().strip()
                print(f"✓ LibreOffice found: {cmd}")
                print(f"  Version: {version}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    print("⚠ LibreOffice not found")
    print("  For best conversion quality, install LibreOffice:")
    print("  - Windows: https://www.libreoffice.org/download/")
    print("  - Linux: sudo apt-get install libreoffice")
    print("  - macOS: brew install libreoffice")
    return False


def test_ms_office():
    """Test if Microsoft Office is available"""
    print("\nTesting Microsoft Office availability...\n")
    
    try:
        from src.converters.ms_office_converter import MSOfficeConverter
        
        converter = MSOfficeConverter()
        if converter.is_available():
            print("✓ Microsoft Office found")
            if converter._word_path:
                print(f"  Word: {converter._word_path}")
            if converter._excel_path:
                print(f"  Excel: {converter._excel_path}")
            if converter._powerpoint_path:
                print(f"  PowerPoint: {converter._powerpoint_path}")
            return True
        else:
            print("⚠ Microsoft Office not found")
            return False
            
    except Exception as e:
        print(f"⚠ Could not check MS Office: {e}")
        return False


def test_converter():
    """Test basic converter functionality"""
    print("\nTesting DocumentConverter class...\n")
    
    try:
        from src.document_converter import DocumentConverter
        from pathlib import Path
        import tempfile
        
        # Create temporary directories
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            
            # Create converter (will create directories)
            converter = DocumentConverter(str(input_dir), str(output_dir))
            
            print(f"✓ DocumentConverter initialized")
            print(f"  Input: {converter.input_dir}")
            print(f"  Output: {converter.output_dir}")
            
            # Test find_all_documents
            docs = converter.find_all_documents()
            print(f"✓ find_all_documents() works (found {len(docs)} documents)")
            
            # Test converter availability
            available = converter.converter_factory.get_available_converters_info()
            print(f"✓ Available converters:")
            for name, status in available.items():
                status_str = "Available" if status else "Not available"
                print(f"    {name}: {status_str}")
            
        print("\n✅ DocumentConverter class works correctly!")
        return True
        
    except Exception as e:
        print(f"✗ Error testing DocumentConverter: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 70)
    print("Document Converter v2.0 - Installation Test")
    print("=" * 70)
    print()
    
    # Test imports
    imports_ok = test_imports()
    
    # Test LibreOffice
    libreoffice_ok = test_libreoffice()
    
    # Test MS Office
    ms_office_ok = test_ms_office()
    
    # Test converter
    converter_ok = test_converter()
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Dependencies:      {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"LibreOffice:       {'✅ AVAILABLE' if libreoffice_ok else '⚠ NOT FOUND'}")
    print(f"Microsoft Office:  {'✅ AVAILABLE' if ms_office_ok else '⚠ NOT FOUND'}")
    print(f"Converter:         {'✅ PASS' if converter_ok else '❌ FAIL'}")
    print()
    
    if imports_ok and converter_ok:
        print("🎉 Installation successful! Ready to convert documents.")
        print()
        print("Quick start:")
        print("  python main.py                              # Uses ./input and ./output")
        print("  python main.py <input_folder> <output_folder>")
        print()
        
        # Recommendations
        if not libreoffice_ok and not ms_office_ok:
            print("⚠ Recommendation: Install LibreOffice or MS Office for best quality")
        elif libreoffice_ok and ms_office_ok:
            print("✓ Excellent! Both LibreOffice and MS Office available")
        elif libreoffice_ok:
            print("✓ LibreOffice available - excellent conversion quality")
        elif ms_office_ok:
            print("✓ MS Office available - excellent conversion quality")
        
        return 0
    else:
        print("⚠ Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
