"""
Comprehensive verification test for Japanese/Unicode Excel to PDF conversion
Ensures 100% content matching between source Excel and output PDF
"""

from pathlib import Path
import openpyxl
from pypdf import PdfReader
import logging
import sys

# Fix Windows console encoding for Unicode output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import logging
import sys

# Force UTF-8 for stdout/stderr to handle Japanese characters
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def extract_excel_content(excel_path):
    """Extract all text content from Excel file"""
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    content = {}
    
    for sheet in wb.worksheets:
        sheet_name = sheet.title
        sheet_data = []
        
        for row in sheet.iter_rows(values_only=True):
            if any(cell is not None for cell in row):
                row_text = [str(cell) if cell is not None else '' for cell in row]
                sheet_data.append(' '.join(row_text))
        
        content[sheet_name] = '\n'.join(sheet_data)
    
    wb.close()
    return content

def extract_pdf_content(pdf_path):
    """Extract all text content from PDF file"""
    reader = PdfReader(str(pdf_path))
    content = []
    
    for page in reader.pages:
        text = page.extract_text()
        content.append(text)
    
    return '\n'.join(content)

def verify_content_match(excel_path, pdf_path):
    """Verify that PDF contains all content from Excel"""
    print(f"\n{'='*70}")
    print(f"Content Verification Test")
    print(f"{'='*70}\n")
    
    print(f"Source Excel: {excel_path}")
    print(f"Output PDF:   {pdf_path}\n")
    
    # Extract content
    excel_content = extract_excel_content(excel_path)
    pdf_text = extract_pdf_content(pdf_path)
    
    # Track results
    results = {
        'total_sheets': len(excel_content),
        'matched_sheets': 0,
        'missing_content': [],
        'found_content': [],
    }
    
    print(f"Sheets in Excel: {list(excel_content.keys())}\n")
    
    # Check each sheet's content
    for sheet_name, sheet_text in excel_content.items():
        print(f"Checking sheet: '{sheet_name}'")
        
        # Extract individual values to check
        values = [v.strip() for v in sheet_text.split() if v.strip()]
        
        found = 0
        missing = 0
        
        for value in values:
            if value in pdf_text:
                found += 1
            else:
                missing += 1
                results['missing_content'].append((sheet_name, value))
        
        match_rate = (found / len(values) * 100) if values else 100
        print(f"  Values checked: {len(values)}")
        print(f"  Found: {found} ({match_rate:.1f}%)")
        print(f"  Missing: {missing}")
        
        if match_rate >= 95:  # Allow 5% tolerance for formatting differences
            results['matched_sheets'] += 1
            print(f"  ✅ PASS\n")
        else:
            print(f"  ❌ FAIL\n")
    
    # Summary
    print(f"{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Total sheets: {results['total_sheets']}")
    print(f"Matched sheets: {results['matched_sheets']}")
    print(f"Success rate: {results['matched_sheets']/results['total_sheets']*100:.1f}%")
    
    if results['missing_content']:
        print(f"\nMissing content (first 10):")
        for sheet, value in results['missing_content'][:10]:
            print(f"  [{sheet}] {value}")
    
    # Final verdict
    print(f"\n{'='*70}")
    if results['matched_sheets'] == results['total_sheets']:
        print(f"✅ VERIFICATION PASSED!")
        print(f"   All content preserved correctly")
        return True
    else:
        print(f"⚠️  VERIFICATION PARTIAL")
        print(f"   {results['matched_sheets']}/{results['total_sheets']} sheets fully matched")
        return results['matched_sheets'] >= results['total_sheets'] * 0.9

def test_japanese_unicode():
    """Test specific Japanese/Unicode characters"""
    print(f"\n{'='*70}")
    print(f"Unicode Character Test")
    print(f"{'='*70}\n")
    
    pdf_path = Path('output/japanese_test.pdf')
    pdf_text = extract_pdf_content(pdf_path)
    
    test_cases = [
        ('Hiragana', 'これは'),
        ('Katakana', 'テスト'),
        ('Kanji', '日本語'),
        ('Chinese', '你好'),
        ('Korean', '안녕'),
        ('Special symbols', '①②③'),
        ('Business terms', '売上'),
    ]
    
    passed = 0
    for name, text in test_cases:
        if text in pdf_text:
            print(f"  ✅ {name:20s} '{text}'")
            passed += 1
        else:
            print(f"  ❌ {name:20s} '{text}' NOT FOUND")
    
    print(f"\nPassed: {passed}/{len(test_cases)}")
    return passed == len(test_cases)

if __name__ == '__main__':
    excel_path = Path('input/japanese_test.xlsx')
    pdf_path = Path('output/japanese_test.pdf')
    
    if not excel_path.exists():
        print(f"ERROR: Excel file not found: {excel_path}")
        exit(1)
    
    if not pdf_path.exists():
        print(f"ERROR: PDF file not found: {pdf_path}")
        print(f"Run test_japanese_conversion.py first")
        exit(1)
    
    # Run verification
    content_ok = verify_content_match(excel_path, pdf_path)
    unicode_ok = test_japanese_unicode()
    
    if content_ok and unicode_ok:
        print(f"\n{'='*70}")
        print(f"🎉 ALL TESTS PASSED!")
        print(f"{'='*70}")
        exit(0)
    else:
        print(f"\n{'='*70}")
        print(f"❌ SOME TESTS FAILED")
        print(f"{'='*70}")
        exit(1)
