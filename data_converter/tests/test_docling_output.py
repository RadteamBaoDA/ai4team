#!/usr/bin/env python3
"""
Quick test for Docling converter output issue.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.converters.docling_converter import DoclingConverter

def test_docling_output():
    """Test if Docling converter produces output"""
    print("=" * 60)
    print("Testing Docling Converter Output")
    print("=" * 60)
    
    # Check if Docling is available
    converter = DoclingConverter()
    if not converter.is_available():
        print("\n❌ Docling not available. Install with:")
        print("   pip install docling")
        return False
    
    print("\n✅ Docling is available")
    
    # Check test files
    test_dir = Path(__file__).parent / "input" / "docling_test"
    if not test_dir.exists():
        print(f"\n⚠️  Test directory not found: {test_dir}")
        print("Generate test files with:")
        print("   python generate_test_excel.py")
        return False
    
    test_files = list(test_dir.glob("*.xlsx"))
    if not test_files:
        print(f"\n⚠️  No Excel files in {test_dir}")
        print("Generate test files with:")
        print("   python generate_test_excel.py")
        return False
    
    print(f"\n📁 Found {len(test_files)} test file(s)")
    
    # Test conversion
    output_dir = Path(__file__).parent / "output" / "docling_debug"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for test_file in test_files[:1]:  # Test first file only
        print(f"\n🔄 Testing: {test_file.name}")
        output_file = output_dir / f"{test_file.stem}_docling.pdf"
        
        try:
            success = converter.convert(test_file, output_file)
            
            if success and output_file.exists():
                size = output_file.stat().st_size
                print(f"✅ Conversion successful!")
                print(f"   Output: {output_file}")
                print(f"   Size: {size:,} bytes")
                
                if size < 1000:
                    print(f"   ⚠️  Warning: File size is very small ({size} bytes)")
                    print(f"   This might indicate empty or minimal content")
                    return False
                else:
                    print(f"   ✅ File size looks good")
                    return True
            else:
                print(f"❌ Conversion failed")
                print(f"   Output exists: {output_file.exists()}")
                return False
                
        except Exception as e:
            print(f"❌ Error during conversion: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == "__main__":
    success = test_docling_output()
    print("\n" + "=" * 60)
    if success:
        print("✅ Docling converter is working correctly!")
    else:
        print("❌ Docling converter has issues")
        print("\nTroubleshooting:")
        print("1. Check logs in logs/ directory")
        print("2. Verify Docling version: pip show docling")
        print("3. Try updating: pip install --upgrade docling")
        print("4. Check if openpyxl fallback is being used")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
