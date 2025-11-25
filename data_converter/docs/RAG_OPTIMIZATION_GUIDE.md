# RAG & Knowledge Base Optimization Guide

## Overview

This document describes the RAG (Retrieval-Augmented Generation) and Knowledge Base optimization features for document-to-PDF conversion, specifically designed for integration with **Ragflow** and **AnythingLLM**.

## Quick Start

Enable all RAG optimizations with a single environment variable:

```bash
export RAG_OPTIMIZATION_ENABLED=true
```

### Advanced: Docling Integration (Optional)

For **complex Excel tables** with merged cells, irregular layouts, or sophisticated structures, enable the Docling converter for enhanced layout recognition:

```bash
export USE_DOCLING_CONVERTER=true
export DOCLING_PRIORITY=2  # 0=disabled, 1=fallback, 2=recommended, 3=before LibreOffice, 4=before MS Office
```

**See:** [Docling Integration Guide](./DOCLING_INTEGRATION.md) for complete setup and usage documentation.

## Master Toggle

### `RAG_OPTIMIZATION_ENABLED` (default: `true`)

Controls ALL RAG-specific features. When set to `false`, exports use standard PDF settings without RAG enhancements.

## RAG Features by Document Type

### Word Documents (.docx, .doc)

**Enabled Features:**
- **PDF Bookmarks**: Automatically created from heading styles (Heading 1, 2, 3, etc.)
- **Tagged PDF Structure**: Enables semantic parsing of document hierarchy
- **PDF/A Compliance**: Ensures font embedding and long-term archival
- **Document Metadata**: Title, keywords, source filename, page count, conversion date

**Settings:**
```bash
WORD_CREATE_HEADING_BOOKMARKS=true   # PDF outline from headings
WORD_ADD_DOC_PROPERTIES=true         # Inject metadata
WORD_PRESERVE_STRUCTURE_TAGS=true    # Tagged PDF for parsing
```

**Benefits for RAG:**
- Bookmarks enable semantic chunking by section
- Metadata improves vector search relevance
- Structure tags help AI understand document hierarchy

### Excel Spreadsheets (.xlsx, .xls)

**Enabled Features:**
- **Table Detection**: Automatically identifies table structures
- **Smart Pagination**: Limits rows per page (default: 15) for better parsing
- **Row/Column Headers**: A, B, C... and 1, 2, 3... printed for cell referencing
- **Gridlines**: Improves table structure recognition
- **Citation Headers/Footers**: Filename, sheet name, page numbers on every page
- **Frozen Panes**: Automatically repeats header rows on each page
- **Document Metadata**: Workbook-level title, keywords, sheet count

**Settings:**
```bash
EXCEL_TABLE_OPTIMIZATION=true          # Enable table detection
EXCEL_TABLE_MAX_ROWS_PER_PAGE=15       # Max rows per page in tables
EXCEL_PRINT_ROW_COL_HEADERS=true       # Print A,B,C and 1,2,3
EXCEL_PRINT_GRIDLINES=true             # Print gridlines
EXCEL_ADD_CITATION_HEADERS=true        # Add filename/sheet/page info
EXCEL_PAGE_BREAK_ON_EMPTY_ROWS=1       # Page break after N empty rows
EXCEL_PAGE_BREAK_CHAR='<<<PAGE_BREAK>>>'  # Manual page break trigger
```

**Citation Format:**
- **Header**: `[Filename] | [Sheet: SheetName]`
- **Footer**: `Date | Page X of Y`

**Benefits for RAG:**
- Table pagination ensures manageable chunks for vector DB
- Headers/gridlines improve OCR and table parsing
- Cell references (A1, B2) enable precise citations
- Sheet context helps multi-sheet workbook navigation

### PowerPoint Presentations (.pptx, .ppt)

**Enabled Features:**
- **Slide Numbers**: Added to all slides
- **PDF Outline**: Created from slide titles (when available)
- **Citation Footers**: Filename and date stamped on each slide
- **Document Metadata**: Title, keywords, slide count
- **Font Embedding**: Ensures consistent rendering

**Settings:**
```bash
PPTX_ADD_SLIDE_NUMBERS=true      # Add slide numbers
PPTX_CREATE_OUTLINE=true         # Bookmarks from titles
PPTX_ADD_DOC_PROPERTIES=true     # Inject metadata
PPTX_NOTES_AS_TEXT=false         # Include speaker notes (optional)
```

**Benefits for RAG:**
- Slide numbers enable precise citations ("Slide 5")
- Outline helps navigate presentation structure
- Footers provide source context on every page

## PDF Export Settings

### General PDF Settings

```bash
PDF_CREATE_BOOKMARKS=true    # Create PDF outline
PDF_CREATE_TAGGED=true       # Tagged PDF for accessibility
PDF_EMBED_FONTS=true         # Embed all fonts
PDF_USE_ISO19005=true        # PDF/A-1 compliance
```

### Citation Settings

```bash
CITATION_INCLUDE_FILENAME=true       # Include source filename
CITATION_INCLUDE_DATE=true           # Include conversion date
CITATION_INCLUDE_PAGE=true           # Include page/sheet/slide count
CITATION_DATE_FORMAT='%Y-%m-%d'      # Date format (default: 2025-11-25)
```

## Converter Priority

Converters are tried in this order:

1. **Microsoft Office** (COM automation - Windows only)
   - Highest quality, native features
   - Full RAG optimization support

2. **LibreOffice** (Command-line)
   - Cross-platform
   - RAG features via filter options + pypdf metadata injection

3. **Python Libraries** (Fallback)
   - docx2pdf, openpyxl, python-pptx, reportlab
   - RAG features via pypdf metadata injection

## Integration with Ragflow

### Recommended Settings for Ragflow

```bash
# Enable RAG
RAG_OPTIMIZATION_ENABLED=true

# Excel: Optimize for table parsing
EXCEL_TABLE_OPTIMIZATION=true
EXCEL_TABLE_MAX_ROWS_PER_PAGE=15
EXCEL_PRINT_GRIDLINES=true
EXCEL_PRINT_ROW_COL_HEADERS=true

# Enable bookmarks for semantic chunking
PDF_CREATE_BOOKMARKS=true
WORD_CREATE_HEADING_BOOKMARKS=true
PPTX_CREATE_OUTLINE=true

# Enable citations
CITATION_INCLUDE_FILENAME=true
CITATION_INCLUDE_PAGE=true
CITATION_INCLUDE_DATE=true
```

### Ragflow Benefits

- **Bookmarks**: Used for intelligent document chunking
- **Table Pagination**: Prevents oversized table chunks
- **Metadata**: Improves document search and filtering
- **Citations**: Headers/footers enable precise source attribution

## Integration with AnythingLLM

### Recommended Settings for AnythingLLM

```bash
# Enable RAG
RAG_OPTIMIZATION_ENABLED=true

# Metadata for search
PDF_CREATE_TAGGED=true
WORD_ADD_DOC_PROPERTIES=true
PPTX_ADD_DOC_PROPERTIES=true

# Citations for chat UI
CITATION_INCLUDE_FILENAME=true
CITATION_INCLUDE_PAGE=true
EXCEL_ADD_CITATION_HEADERS=true
```

### AnythingLLM Benefits

- **Tagged PDFs**: Better text extraction and structure parsing
- **Metadata**: Enhanced document search in knowledge base
- **Citations**: Chat responses can reference "Sheet: Sales, Page 3"

## Troubleshooting

### Missing Bookmarks

**Issue**: PDF has no bookmarks/outline

**Solutions**:
- **Word**: Ensure document uses heading styles (Heading 1, 2, 3)
- **Excel**: Bookmarks not supported by Excel COM API (use sheet names in citations instead)
- **PowerPoint**: Bookmarks created from slide titles; ensure slides have title placeholders
- **LibreOffice**: Check `ExportBookmarks=true` in filter options

### Table Not Paginated

**Issue**: Excel table exports as single page

**Solutions**:
- Verify `EXCEL_TABLE_OPTIMIZATION=true`
- Check `EXCEL_TABLE_MAX_ROWS_PER_PAGE > 0`
- Ensure table is detected (at least 3 rows, 2+ columns with consistent data)
- Check logs for "Table detected" message

### Missing Metadata

**Issue**: PDF metadata fields are empty

**Solutions**:
- Verify `RAG_OPTIMIZATION_ENABLED=true`
- For LibreOffice/Python converters: Install `pypdf` (`pip install pypdf>=5.1.0`)
- Check `WORD_ADD_DOC_PROPERTIES=true` or `PPTX_ADD_DOC_PROPERTIES=true`

### Citations Not Appearing

**Issue**: No filename/date in headers/footers

**Solutions**:
- Verify `EXCEL_ADD_CITATION_HEADERS=true` (for Excel)
- Check `CITATION_INCLUDE_FILENAME=true` and `CITATION_INCLUDE_DATE=true`
- Ensure `RAG_OPTIMIZATION_ENABLED=true`

## Performance Tuning

### Large Excel Files

For Excel files with thousands of rows:

```bash
# Increase max rows per page for fewer pages
EXCEL_TABLE_MAX_ROWS_PER_PAGE=30

# Disable gridlines to reduce file size
EXCEL_PRINT_GRIDLINES=false

# Use black and white for smaller PDFs
EXCEL_BLACK_AND_WHITE=true
```

### Batch Processing

```bash
# Enable parallel processing
PARALLEL_MODE=true
MAX_WORKERS=4
BATCH_SIZE=10

# Use process isolation for stability
USE_PROCESS_ISOLATION=true

# Enable memory optimization
MEMORY_OPTIMIZATION=true
```

## Environment Variables Reference

### RAG Master Toggle
- `RAG_OPTIMIZATION_ENABLED` (bool, default: `true`)

### Word Settings
- `WORD_CREATE_HEADING_BOOKMARKS` (bool, default: `true`)
- `WORD_ADD_DOC_PROPERTIES` (bool, default: `true`)
- `WORD_PRESERVE_STRUCTURE_TAGS` (bool, default: `true`)

### Excel Settings
- `EXCEL_TABLE_OPTIMIZATION` (bool, default: `true`)
- `EXCEL_TABLE_MAX_ROWS_PER_PAGE` (int, default: `15`)
- `EXCEL_PRINT_ROW_COL_HEADERS` (bool, default: `true`)
- `EXCEL_PRINT_GRIDLINES` (bool, default: `true`)
- `EXCEL_ADD_CITATION_HEADERS` (bool, default: `true`)
- `EXCEL_BLACK_AND_WHITE` (bool, default: `false`)
- `EXCEL_PAGE_BREAK_ON_EMPTY_ROWS` (int, default: `1`)
- `EXCEL_PAGE_BREAK_CHAR` (string, default: `'<<<PAGE_BREAK>>>'`)

### PowerPoint Settings
- `PPTX_ADD_SLIDE_NUMBERS` (bool, default: `true`)
- `PPTX_CREATE_OUTLINE` (bool, default: `true`)
- `PPTX_ADD_DOC_PROPERTIES` (bool, default: `true`)
- `PPTX_NOTES_AS_TEXT` (bool, default: `false`)

### PDF Export Settings
- `PDF_CREATE_BOOKMARKS` (bool, default: `true`)
- `PDF_CREATE_TAGGED` (bool, default: `true`)
- `PDF_EMBED_FONTS` (bool, default: `true`)
- `PDF_USE_ISO19005` (bool, default: `true`)

### Citation Settings
- `CITATION_INCLUDE_FILENAME` (bool, default: `true`)
- `CITATION_INCLUDE_DATE` (bool, default: `true`)
- `CITATION_INCLUDE_PAGE` (bool, default: `true`)
- `CITATION_DATE_FORMAT` (string, default: `'%Y-%m-%d'`)

## Examples

### Example 1: Optimize for Vector Database Chunking

```bash
export RAG_OPTIMIZATION_ENABLED=true
export PDF_CREATE_BOOKMARKS=true
export WORD_CREATE_HEADING_BOOKMARKS=true
export EXCEL_TABLE_MAX_ROWS_PER_PAGE=15
python main.py --input ./documents --output ./pdfs
```

### Example 2: Maximize Citation Context

```bash
export RAG_OPTIMIZATION_ENABLED=true
export CITATION_INCLUDE_FILENAME=true
export CITATION_INCLUDE_DATE=true
export CITATION_INCLUDE_PAGE=true
export EXCEL_ADD_CITATION_HEADERS=true
export EXCEL_PRINT_ROW_COL_HEADERS=true
python main.py --input ./documents --output ./pdfs
```

### Example 3: Disable RAG for Standard Export

```bash
export RAG_OPTIMIZATION_ENABLED=false
python main.py --input ./documents --output ./pdfs
```

## Known Limitations

1. **Excel Sheet Bookmarks**: Excel COM API does not support per-sheet bookmarks. Use citation headers to identify sheets instead.

2. **PowerPoint Bookmarks**: Only created when slides have title placeholders. Empty slides won't generate bookmarks.

3. **LibreOffice Filters**: Some filter options may vary by LibreOffice version. Tested with LibreOffice 7.x+.

4. **Python Converters**: Fallback converters have limited formatting fidelity compared to native Office exports.

## Version History

- **v2.6**: RAG optimization features added (bookmarks, metadata, table pagination, citations)
- **v2.5**: Parallel processing and memory optimization
- **v2.4**: Excel RAG enhancements
- **v2.3**: Initial RAG support

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Verify environment variables are set correctly
3. Test with `RAG_OPTIMIZATION_ENABLED=false` to isolate RAG-specific issues
4. Review this guide's troubleshooting section
