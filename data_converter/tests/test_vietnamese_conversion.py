"""
Test Docling converter with Vietnamese Excel file
"""

from pathlib import Path
from src.converters.docling_converter import DoclingConverter
import logging
import sys

# Force UTF-8 for stdout/stderr
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_vietnamese_conversion():
    """Test Vietnamese Excel to PDF conversion"""
    input_file = Path('input/vietnamese_test.xlsx')
    output_file = Path('output/vietnamese_test.pdf')
    
    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        return False
    
    # Create output directory
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Test conversion
    converter = DoclingConverter()
    
    print(f"\n{'='*60}")
    print(f"Testing Vietnamese Excel → PDF Conversion")
    print(f"{'='*60}")
    print(f"Input:  {input_file}")
    print(f"Output: {output_file}")
    print()
    
    success = converter.convert(input_file, output_file)
    
    if success and output_file.exists():
        file_size = output_file.stat().st_size
        print(f"\n✅ SUCCESS!")
        print(f"   Output file created: {output_file}")
        print(f"   File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        
        # Verify PDF content
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(output_file))
            print(f"   Pages: {len(reader.pages)}")
            
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            print(f"\n   Content Preview:")
            print(f"   {text[:200]}...")
            
            # Check specific Vietnamese characters
            test_chars = ['Nguyễn', 'Hà Nội', 'Đà Nẵng', 'Ư', 'Ơ', 'ă', 'â', 'ê', 'ô', 'ơ', 'ư']
            print(f"\n   Character Check:")
            for char in test_chars:
                if char in text:
                    print(f"   ✅ Found '{char}'")
                else:
                    print(f"   ❌ Missing '{char}'")
                    
        except Exception as e:
            print(f"   (Could not read PDF: {e})")
        
        return True
    else:
        print(f"\n❌ FAILED!")
        return False

if __name__ == '__main__':
    test_vietnamese_conversion()
