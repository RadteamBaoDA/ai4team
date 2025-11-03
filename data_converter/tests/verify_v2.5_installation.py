#!/usr/bin/env python3
"""
Version 2.5 Installation Verification Script

This script verifies that all v2.5 components are properly installed and functional.
Run this after installing v2.5 to ensure everything is working correctly.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80)

def print_status(check, status, message=""):
    """Print status with emoji"""
    emoji = "✅" if status else "❌"
    print(f"{emoji} {check:<40} {'PASS' if status else 'FAIL':<10} {message}")

def verify_v25_installation():
    """Verify all v2.5 components"""
    print_header("VERSION 2.5 INSTALLATION VERIFICATION")
    
    all_passed = True
    
    # Check 1: Core imports
    print("\n[1/8] Checking core imports...")
    try:
        from src.document_converter import DocumentConverter
        print_status("DocumentConverter import", True)
    except Exception as e:
        print_status("DocumentConverter import", False, str(e))
        all_passed = False
    
    # Check 2: Hash cache module
    print("\n[2/8] Checking hash cache module...")
    try:
        from src.utils.hash_cache import HashCache, get_hash_cache
        cache = get_hash_cache()
        print_status("HashCache import", True)
        print_status("HashCache singleton", True, f"DB at {cache.db_path}")
    except Exception as e:
        print_status("HashCache module", False, str(e))
        all_passed = False
    
    # Check 3: tqdm availability
    print("\n[3/8] Checking tqdm availability...")
    try:
        import tqdm
        print_status("tqdm installed", True, f"Version {tqdm.__version__}")
    except ImportError:
        print_status("tqdm installed", False, "Install with: pip install tqdm>=4.66.0")
        print_status("Fallback mode", True, "Converter will work without progress bars")
    
    # Check 4: v2.5 methods
    print("\n[4/8] Checking v2.5 methods...")
    try:
        from src.document_converter import DocumentConverter
        converter = DocumentConverter()
        
        methods = [
            '_get_file_size',
            '_categorize_by_size',
            '_calculate_adaptive_workers',
            '_sort_by_priority'
        ]
        
        for method in methods:
            has_method = hasattr(converter, method)
            print_status(f"Method {method}", has_method)
            if not has_method:
                all_passed = False
    except Exception as e:
        print_status("Method verification", False, str(e))
        all_passed = False
    
    # Check 5: v2.5 attributes
    print("\n[5/8] Checking v2.5 attributes...")
    try:
        from src.document_converter import DocumentConverter
        converter = DocumentConverter()
        
        attributes = [
            ('enable_progress_bar', True),
            ('adaptive_workers', True),
            ('priority_large_files', True),
            ('batch_small_files', True),
            ('SMALL_FILE_THRESHOLD', 100 * 1024),
            ('LARGE_FILE_THRESHOLD', 10 * 1024 * 1024)
        ]
        
        for attr_name, expected in attributes:
            has_attr = hasattr(converter, attr_name)
            if has_attr:
                value = getattr(converter, attr_name)
                if attr_name.endswith('_THRESHOLD'):
                    print_status(f"Attribute {attr_name}", value == expected, f"= {value}")
                else:
                    print_status(f"Attribute {attr_name}", value == expected, f"= {value}")
            else:
                print_status(f"Attribute {attr_name}", False)
                all_passed = False
    except Exception as e:
        print_status("Attribute verification", False, str(e))
        all_passed = False
    
    # Check 6: File hash with persistent cache
    print("\n[6/8] Checking file hash with persistent cache...")
    try:
        # Read the file_hash.py source to check for the parameter
        file_hash_path = Path("src/utils/file_hash.py")
        if file_hash_path.exists():
            content = file_hash_path.read_text()
            has_param = "use_persistent_cache" in content and "use_persistent_cache: bool = True" in content
            print_status("Persistent cache parameter", has_param)
            
            # Also check if it imports hash_cache
            has_import = "from .hash_cache import get_hash_cache" in content
            print_status("Persistent cache integration", has_import)
            
            if not (has_param and has_import):
                all_passed = False
        else:
            print_status("File hash module", False, "file_hash.py not found")
            all_passed = False
    except Exception as e:
        print_status("File hash verification", False, str(e))
        all_passed = False
    
    # Check 7: Documentation files
    print("\n[7/8] Checking documentation files...")
    docs = [
        ("WHATS_NEW_V2.5.md", Path("WHATS_NEW_V2.5.md")),
        ("QUICKREF_V2.5.md", Path("docs/QUICKREF_V2.5.md")),
        ("V2.5_COMPLETION_REPORT.md", Path("docs/V2.5_COMPLETION_REPORT.md")),
        ("V2.5_INDEX.md", Path("docs/V2.5_INDEX.md")),
        ("CHANGELOG.md", Path("docs/CHANGELOG.md"))
    ]
    
    for doc_name, doc_path in docs:
        exists = doc_path.exists()
        print_status(f"Documentation: {doc_name}", exists, f"at {doc_path}")
        if not exists:
            all_passed = False
    
    # Check 8: Test file
    print("\n[8/8] Checking test files...")
    test_file = Path("tests/test_v2.5_features.py")
    exists = test_file.exists()
    print_status("Test suite", exists, f"at {test_file}")
    if not exists:
        all_passed = False
    
    # Final summary
    print_header("VERIFICATION SUMMARY")
    
    if all_passed:
        print("\n✅ ALL CHECKS PASSED!")
        print("\nVersion 2.5 is properly installed and ready to use.")
        print("\nNext steps:")
        print("  1. Run tests: python tests/test_v2.5_features.py")
        print("  2. Try conversion: python main.py")
        print("  3. Read docs: WHATS_NEW_V2.5.md")
        return 0
    else:
        print("\n❌ SOME CHECKS FAILED")
        print("\nPlease fix the issues above and run this script again.")
        print("\nCommon fixes:")
        print("  - Install tqdm: pip install tqdm>=4.66.0")
        print("  - Reinstall: pip install -r requirements.txt")
        print("  - Check git status: git status")
        return 1

if __name__ == "__main__":
    sys.exit(verify_v25_installation())
