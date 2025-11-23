# Document Converter v2.1

## New Features

This is a **test markdown file** to demonstrate the new text file conversion feature.

### Supported Formats

1. CSV files
2. Text files (.txt)
3. Markdown files (.md)
4. HTML files
5. OpenDocument formats

### How It Works

The converter now supports:
- Converting text-based files to PDF
- Copying PDF and image files directly
- Maintaining folder structure

### Example

```python
from src.document_converter import DocumentConverter

converter = DocumentConverter()
stats = converter.convert_all()
```

That's it! Simple and effective.
