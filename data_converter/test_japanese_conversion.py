"""
Test Docling converter with Japanese Excel file
"""

from pathlib import Path
from src.converters.docling_converter import DoclingConverter
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_japanese_conversion():
    """Test Japanese Excel to PDF conversion"""
    input_file = Path('input/japanese_test.xlsx')
    output_file = Path('output/japanese_test.pdf')
    
    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        return False
    
    # Create output directory
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Test conversion
    converter = DoclingConverter()
    
    if not converter.is_available():
        print("ERROR: Docling converter not available!")
        print("Install with: pip install docling")
        return False
    
    print(f"\n{'='*60}")
    print(f"Testing Japanese Excel → PDF Conversion")
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
        
        # Verify PDF can be read
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(output_file))
            print(f"   Pages: {len(reader.pages)}")
            
            # Try to extract text to verify encoding
            if len(reader.pages) > 0:
                text = reader.pages[0].extract_text()
                print(f"   First page text preview:")
                print(f"   {text[:200]}...")
        except Exception as e:
            print(f"   (Could not read PDF: {e})")
        
        return True
    else:
        print(f"\n❌ FAILED!")
        print(f"   Conversion failed or output file not created")
        return False

if __name__ == '__main__':
    result = test_japanese_conversion()
    exit(0 if result else 1)
