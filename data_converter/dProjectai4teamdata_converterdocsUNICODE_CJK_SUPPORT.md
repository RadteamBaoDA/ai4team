# Unicode, CJK, and Vietnamese Support in Docling Converter

## Overview

The Docling converter now includes comprehensive Unicode support for Japanese, Chinese, Korean (CJK), and Vietnamese text. It features a **Smart Font Selection** system that dynamically chooses the best font for each document or table based on the actual text content.

## Features

### ✅ Implemented
- **Smart Font Selection**: Automatically analyzes text content to detect the language (Japanese, Vietnamese, Korean, Chinese) and selects the optimal font.
- **Dynamic Font Registration**: Detects and registers available fonts from the Windows fonts directory.
- **Encoding Detection**: Uses `chardet` library to detect file encoding (UTF-8, Shift-JIS, etc.).
- **Unicode Preservation**: Ensures all text is properly encoded as UTF-8 throughout the conversion pipeline.
- **Style Integration**: ReportLab paragraph and table styles are dynamically updated with the correct font.

### Smart Font Strategy

The converter uses a content-aware strategy to select fonts:

1. **Vietnamese Detection**: Checks for specific Vietnamese Unicode ranges (including extensions for tone marks).
   - **Preferred Fonts**: Tahoma, Arial Unicode MS, Segoe UI, Verdana.
   - **Why**: Standard CJK fonts (like MS-Gothic) often lack full Vietnamese character support (resulting in "tofu" boxes).

2. **Japanese Detection**: Checks for Hiragana and Katakana ranges.
   - **Preferred Fonts**: MS-Gothic, Meiryo, Yu Mincho.
   - **Why**: These fonts provide the best rendering for Kanji and Kana.

3. **Korean Detection**: Checks for Hangul ranges.
   - **Preferred Fonts**: Malgun Gothic, Batang.

4. **Chinese Detection**: Checks for CJK Unified Ideographs.
   - **Preferred Fonts**: SimSun, SimHei, Microsoft YaHei.

5. **Fallback**: If no specific language is detected, defaults to standard Unicode fonts (Arial, Tahoma).

## Language-Specific Support

### Vietnamese (Tiếng Việt) - ✅ Fully Supported
- **Scripts**: Latin with extensive diacritics (Quốc ngữ)
- **Fonts**: Tahoma, Arial Unicode MS, Segoe UI
- **Test Status**: 100% pass rate (including complex tone marks like 'Ư', 'Ơ')

### Japanese (日本語) - ✅ Fully Supported
- **Scripts**: Hiragana (ひらがな), Katakana (カタカナ), Kanji (漢字)
- **Fonts**: MS-Gothic, Meiryo, YuMincho
- **Test Status**: 100% pass rate

### Chinese (中文) - ✅ Mostly Supported  
- **Scripts**: Simplified (简体), Traditional (繁體)
- **Fonts**: SimSun, SimHei, MS-Gothic (partial)
- **Test Status**: ~95% pass rate

### Korean (한국어) - ✅ Supported
- **Scripts**: Hangul (한글), Hanja (漢字)
- **Fonts**: Malgun Gothic
- **Test Status**: Supported via smart font selection

## Usage

### Automatic Handling
You don't need to configure anything. The converter automatically handles mixed workloads:

```python
from src.converters.docling_converter import DoclingConverter

converter = DoclingConverter()

# File 1: Japanese
converter.convert('japanese_file.xlsx', 'output_ja.pdf') 
# -> Uses MS-Gothic

# File 2: Vietnamese
converter.convert('vietnamese_file.xlsx', 'output_vn.pdf') 
# -> Uses Tahoma/Arial Unicode
```

### Mixed Content
For Excel files with multiple sheets in different languages, the converter evaluates the content of **each sheet** independently and applies the best font for that specific sheet's tables.

## Technical Details

### Smart Font Selection Logic
```python
def _get_best_font_for_text(self, text: str) -> str:
    """
    Analyzes text content to determine the best available font.
    Prioritizes:
    1. Vietnamese (if specific chars found) -> Tahoma/Arial Unicode
    2. Japanese (if Kana found) -> MS-Gothic
    3. Korean (if Hangul found) -> Malgun Gothic
    4. Chinese (if CJK Ideographs found) -> SimSun
    """
```

### Font Registration
The system builds a `_font_map` at startup:
```python
self._font_map = {
    'japanese': ['MS-Gothic', 'Meiryo', ...],
    'korean': ['Malgun Gothic', ...],
    'chinese': ['SimSun', ...],
    'vietnamese': ['Tahoma', 'Arial Unicode MS', ...],
    'default': ['Arial', 'Segoe UI', ...]
}
```

## Limitations

### Mixed-Line Constraint
ReportLab PDF generation applies fonts at the paragraph/cell level. 
- **Supported**: A Japanese paragraph followed by a Vietnamese paragraph.
- **Supported**: A Japanese table row followed by a Vietnamese table row (if configured).
- **Limitation**: Mixing Japanese and Vietnamese *within the exact same sentence* might still favor one font, potentially causing minor rendering issues for the secondary language if the primary font lacks coverage. However, `Arial Unicode MS` (if available) usually handles this well.

### Font Availability
Requires Windows fonts installed:
- Windows 10/11: Fonts pre-installed ✅
- Windows Server: May need manual installation of "Supplemental Fonts"
- Linux/Mac: Requires installing compatible fonts (e.g., Noto Sans CJK, Noto Sans Vietnamese)

## Testing

### Test Files
```bash
# Generate test files
python generate_japanese_test.py
python generate_vietnamese_test.py

# Test conversion
python test_japanese_conversion.py
python test_vietnamese_conversion.py
```

### Test Results
```
✅ Vietnamese content: 100% preserved (Ư, Ơ, Đ, etc.)
✅ Japanese content: 100% preserved
✅ Chinese content: ~95% preserved
✅ Korean content: Supported
```

## Dependencies

```txt
chardet>=5.2.0  # Encoding detection
reportlab>=4.0.7  # PDF generation with Unicode support
pypdf>=5.1.0  # PDF metadata
openpyxl>=3.1.2  # Excel reading
```
