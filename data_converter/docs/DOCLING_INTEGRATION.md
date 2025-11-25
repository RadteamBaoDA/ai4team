# Docling Integration Guide

## Overview

The **Docling converter** provides advanced layout recognition for complex documents, particularly Excel files with sophisticated table structures. It uses the open-source [Docling library](https://github.com/docling-project/docling) to enhance layout analysis before PDF generation.

## Why Use Docling?

### Key Benefits

1. **Superior Table Recognition**
   - Handles merged cells, borderless tables, and rotated content
   - Accurate detection of complex table structures
   - Better cell boundary recognition

2. **Enhanced Layout Analysis**
   - Semantic understanding of document structure
   - Improved multi-sheet workbook handling
   - Advanced formula and heading detection

3. **Better Excel Support**
   - More accurate table extraction than standard parsers
   - Preserves complex formatting
   - Handles edge cases (rotated tables, mixed content)

### When to Use Docling

**Best For:**
- ✅ Excel files with complex tables (merged cells, irregular layouts)
- ✅ Multi-sheet workbooks requiring semantic analysis
- ✅ Documents with mixed content types (tables + charts + text)
- ✅ Rotated or borderless tables
- ✅ Cross-page table continuations

**Not Needed For:**
- ❌ Simple Excel spreadsheets (standard converters work fine)
- ❌ Word/PowerPoint documents (MS Office converter is already optimal)
- ❌ PDFs (already in target format)

## Installation

### Option 1: Pip Install

```bash
pip install docling
```

### Option 2: Add to Requirements

Uncomment in `requirements.txt`:
```txt
# docling>=2.63.0  # Advanced layout recognition for complex tables
```

Then run:
```bash
pip install -r requirements.txt
```

### Dependencies

Docling will automatically install:
- `docling-core` - Core document processing
- `docling-ibm-models` - Layout models
- `pillow` - Image processing
- `pdfplumber` - PDF parsing
- Other dependencies

## Configuration

### Enable Docling Converter

```bash
export USE_DOCLING_CONVERTER=true
```

### Set Priority Level

```bash
# 0 = Disabled
# 1 = Fallback only (after all other converters)
# 2 = Before Python converters (DEFAULT - recommended)
# 3 = Before LibreOffice
# 4 = Before MS Office (not recommended)
export DOCLING_PRIORITY=2
```

### Recommended Configuration for RAG

```bash
# Enable Docling for complex Excel files
export USE_DOCLING_CONVERTER=true
export DOCLING_PRIORITY=2

# Enable RAG optimizations
export RAG_OPTIMIZATION_ENABLED=true
export EXCEL_TABLE_OPTIMIZATION=true
export EXCEL_TABLE_MAX_ROWS_PER_PAGE=15
```

## Converter Priority

With Docling enabled at priority 2 (default), the converter order is:

```
For Excel Files:
1. Microsoft Office (if available, Windows only)
2. LibreOffice (if available, MS Office not found)
3. Docling (enhanced layout) ← NEW
4. Python openpyxl (basic fallback)

For Word/PowerPoint Files:
1. Microsoft Office
2. LibreOffice
3. Docling (if enabled)
4. Python libraries
```

## Usage Examples

### Example 1: Convert Complex Excel with Docling

```bash
# Enable Docling
export USE_DOCLING_CONVERTER=true
export DOCLING_PRIORITY=2

# Convert with RAG optimization
python main.py --input ./complex_tables.xlsx --output ./output
```

### Example 2: Force Docling for All Office Files

```bash
# Set highest priority (try Docling first)
export USE_DOCLING_CONVERTER=true
export DOCLING_PRIORITY=4

python main.py --input ./documents --output ./pdfs
```

### Example 3: Use Docling Only as Fallback

```bash
# Lowest priority (only if others fail)
export USE_DOCLING_CONVERTER=true
export DOCLING_PRIORITY=1

python main.py --input ./documents --output ./pdfs
```

## How It Works

### Processing Pipeline

```
Excel File
    ↓
Docling Parser (layout analysis)
    ↓
Extract enhanced table structure
    ↓
Apply RAG optimizations
    ↓
ReportLab PDF generation
    ↓
PDF with metadata injection
```

### What Docling Provides

1. **Layout Analysis**
   - Identifies table boundaries
   - Detects merged cells
   - Recognizes headers vs. data rows
   - Understands reading order

2. **Semantic Understanding**
   - Distinguishes formulas from values
   - Identifies chart regions
   - Detects cross-sheet references
   - Preserves worksheet structure

3. **Enhanced Output**
   - Better table HTML representation
   - Accurate cell coordinates
   - Preserved formatting hints
   - Sheet-level metadata

## Performance Considerations

### Speed

- **Docling** is slower than native converters but more accurate
- Typical: 2-3x slower than MS Office, similar to LibreOffice
- Best for quality over speed

### Memory

- Docling uses ML models (layout detection)
- Requires ~1-2 GB RAM for processing
- Use `MEMORY_OPTIMIZATION=true` for large batches

### Recommendations

```bash
# For large batches with Docling
export PARALLEL_MODE=true
export MAX_WORKERS=2  # Reduce workers if using Docling
export BATCH_SIZE=5   # Smaller batches
export MEMORY_OPTIMIZATION=true
export USE_PROCESS_ISOLATION=true
```

## Troubleshooting

### Docling Not Available

**Symptom**: Converter falls back to Python libraries

**Solution**:
```bash
pip install docling
# Verify installation
python -c "import docling; print('Docling OK')"
```

### Layout Not Improved

**Issue**: Docling didn't enhance output

**Checklist**:
1. Verify `USE_DOCLING_CONVERTER=true`
2. Check priority: `DOCLING_PRIORITY >= 2`
3. Ensure file is Excel (.xlsx, .xls)
4. Check logs for "Converting with Docling"

### Memory Errors

**Issue**: Out of memory during conversion

**Solutions**:
```bash
# Reduce workers
export MAX_WORKERS=1

# Enable memory optimization
export MEMORY_OPTIMIZATION=true

# Use process isolation
export USE_PROCESS_ISOLATION=true

# Reduce batch size
export BATCH_SIZE=3
```

### Slow Performance

**Issue**: Docling is too slow

**Solutions**:
1. Lower priority: `DOCLING_PRIORITY=1` (fallback only)
2. Disable for simple files
3. Use for complex tables only
4. Consider GPU acceleration (if available)

## Comparison: Docling vs. Standard Converters

| Feature | MS Office | LibreOffice | Docling | Python Libraries |
|---------|-----------|-------------|---------|------------------|
| **Speed** | ⚡⚡⚡ Fast | ⚡⚡ Medium | ⚡ Slower | ⚡⚡ Medium |
| **Accuracy** | ⭐⭐⭐ High | ⭐⭐ Good | ⭐⭐⭐ High | ⭐ Basic |
| **Complex Tables** | ⭐⭐ Good | ⭐⭐ Good | ⭐⭐⭐ Excellent | ⭐ Poor |
| **Merged Cells** | ⭐⭐⭐ Native | ⭐⭐ Good | ⭐⭐⭐ Excellent | ⭐ Poor |
| **Layout Analysis** | ⭐⭐ Built-in | ⭐⭐ Built-in | ⭐⭐⭐ ML-based | ⭐ Rule-based |
| **Platform** | Windows Only | Cross-platform | Cross-platform | Cross-platform |
| **Dependencies** | Office Install | LO Install | Python only | Python only |
| **RAG Optimized** | ✅ | ✅ | ✅ | ✅ |

### When to Choose Each

**MS Office**: Best overall for Windows users with Office installed

**LibreOffice**: Best for Linux/Mac or when Office unavailable

**Docling**: Best for complex Excel tables, cross-platform ML accuracy

**Python Libraries**: Basic fallback when others unavailable

## Integration with RAG Systems

### Ragflow Integration

Docling enhances Ragflow's table parsing:

```bash
export USE_DOCLING_CONVERTER=true
export RAG_OPTIMIZATION_ENABLED=true
export EXCEL_TABLE_OPTIMIZATION=true
export EXCEL_TABLE_MAX_ROWS_PER_PAGE=15
```

**Benefits**:
- Better table chunking (Docling detects boundaries)
- More accurate cell references
- Improved vector DB quality

### AnythingLLM Integration

Docling improves document search:

```bash
export USE_DOCLING_CONVERTER=true
export PDF_CREATE_TAGGED=true
export CITATION_INCLUDE_FILENAME=true
```

**Benefits**:
- Enhanced metadata extraction
- Better table structure in vector store
- More precise citations

## Advanced Configuration

### Custom Docling Settings

The converter respects all RAG settings:

```bash
# Table pagination
export EXCEL_TABLE_MAX_ROWS_PER_PAGE=20

# Citation headers
export EXCEL_ADD_CITATION_HEADERS=true
export CITATION_INCLUDE_FILENAME=true
export CITATION_INCLUDE_PAGE=true

# Gridlines and headers
export EXCEL_PRINT_GRIDLINES=true
export EXCEL_PRINT_ROW_COL_HEADERS=true
```

### Selective Enabling

Use Docling only for specific patterns:

```bash
# Enable Docling at priority 2 (before Python fallback)
export USE_DOCLING_CONVERTER=true
export DOCLING_PRIORITY=2

# But MS Office/LibreOffice will still be tried first
# Docling activates when they're unavailable or fail
```

## FAQ

**Q: Do I need to install MS Office or LibreOffice to use Docling?**

A: No, Docling works independently. It's a pure Python solution.

**Q: Is Docling better than MS Office for Excel conversion?**

A: MS Office is faster and has native formatting. Docling is better for complex table layout analysis and cross-platform use.

**Q: Can Docling handle PDFs?**

A: Yes, but for PDF → PDF conversion, direct processing is unnecessary. Docling is best for Office formats → PDF.

**Q: Does Docling support GPU acceleration?**

A: Docling uses CPU-based models by default. GPU acceleration may be available in future versions.

**Q: Will Docling slow down my batch processing?**

A: Yes, it's slower than native converters. Use `DOCLING_PRIORITY=1` (fallback only) or reduce `MAX_WORKERS` to balance speed and quality.

**Q: Can I use Docling with parallel processing?**

A: Yes, but reduce `MAX_WORKERS` (e.g., 2-4) due to higher memory usage.

## Version History

- **v2.6**: Docling integration added as optional advanced layout converter
- **v2.5**: RAG optimization features
- **v2.4**: Excel table optimization

## References

- [Docling GitHub](https://github.com/docling-project/docling)
- [Docling Documentation](https://docling-project.github.io/docling/)
- [Docling Technical Report](https://arxiv.org/abs/2408.09869)
- [RAG Optimization Guide](./RAG_OPTIMIZATION_GUIDE.md)

## Support

For issues with Docling integration:
1. Check installation: `pip show docling`
2. Verify environment variables
3. Review logs for "Docling" entries
4. Test with small file first
5. Compare with standard converter output
