# Document Converter v2.0 - Architecture Guide

## Project Structure

```
data_converter/
├── main.py                     # Main entry point
├── requirements.txt            # Python dependencies
│
├── config/                     # Configuration package
│   ├── __init__.py
│   └── settings.py            # Application settings
│
├── src/                        # Source code package
│   ├── __init__.py
│   ├── document_converter.py  # Main DocumentConverter class
│   │
│   ├── converters/            # Converter implementations
│   │   ├── __init__.py
│   │   ├── base_converter.py # Abstract base class
│   │   ├── factory.py         # Converter factory
│   │   ├── libreoffice_converter.py  # LibreOffice converter
│   │   ├── ms_office_converter.py    # MS Office 365 converter
│   │   └── python_converters.py      # Python library converters
│   │
│   └── utils/                 # Utility modules
│       ├── __init__.py
│       ├── logger.py          # Logging configuration
│       └── file_scanner.py    # File scanning utilities
│
├── input/                      # Default input directory (auto-created)
├── output/                     # Default output directory (auto-created)
└── logs/                       # Log files directory (auto-created)
```

## Key Improvements

### 1. **Default Directories**
- Input: `./input` (relative to main.py)
- Output: `./output` (relative to main.py)
- Logs: `./logs` (relative to main.py)
- All directories are auto-created if they don't exist

### 2. **Microsoft Office 365 Support**
- Priority order: LibreOffice → MS Office 365 → Python Libraries
- Automatic detection of MS Office installation
- Uses COM automation (pywin32) for high-quality conversions
- Supports Word, Excel, and PowerPoint

### 3. **Optimized Code Structure**
- **Separation of Concerns**: Each module has a single responsibility
- **Factory Pattern**: ConverterFactory manages converter selection
- **Strategy Pattern**: BaseConverter interface with multiple implementations
- **Configuration Management**: Centralized settings in config package
- **Dependency Injection**: Loose coupling between components

## Converter Priority

The system tries converters in this order:

1. **LibreOffice** (Best quality, cross-platform)
2. **Microsoft Office 365** (High quality, Windows only)
3. **Python Libraries** (Fallback, requires dependencies)

## Usage

### Basic Usage (with defaults)

```bash
# Uses ./input and ./output directories
python main.py
```

### With Custom Directories

```bash
python main.py <input_folder> <output_folder>
```

### Programmatic Usage

```python
from src.document_converter import DocumentConverter

# Use defaults (./input and ./output)
converter = DocumentConverter()

# Or specify directories
converter = DocumentConverter(
    input_dir="./my_documents",
    output_dir="./my_pdfs"
)

# Convert all files
stats = converter.convert_all()
```

## Design Patterns Used

### 1. Factory Pattern
- `ConverterFactory` creates appropriate converters
- Centralizes converter instantiation logic

### 2. Strategy Pattern
- `BaseConverter` defines the interface
- Multiple implementations (LibreOffice, MS Office, Python libs)
- Runtime selection based on availability

### 3. Template Method Pattern
- `convert_file()` defines the algorithm
- Delegates to specific converters

### 4. Dependency Injection
- Components receive dependencies via constructor
- Easy to test and mock

## Module Responsibilities

### config/settings.py
- Application-wide configuration
- Default paths
- Supported extensions
- Converter paths

### src/document_converter.py
- Main orchestration class
- Coordinates file scanning and conversion
- Manages statistics

### src/converters/
- **base_converter.py**: Converter interface
- **factory.py**: Converter selection logic
- **libreoffice_converter.py**: LibreOffice integration
- **ms_office_converter.py**: MS Office COM automation
- **python_converters.py**: Fallback converters

### src/utils/
- **logger.py**: Logging configuration
- **file_scanner.py**: File system operations

## Extension Points

### Adding a New Converter

1. Create a new converter class inheriting from `BaseConverter`:

```python
from .base_converter import BaseConverter

class MyConverter(BaseConverter):
    def is_available(self) -> bool:
        # Check if converter is available
        return True
    
    def convert(self, input_file: Path, output_file: Path) -> bool:
        # Implement conversion logic
        return True
```

2. Register in `ConverterFactory`:

```python
def __init__(self):
    self.my_converter = MyConverter()
    self._primary_converters.append(self.my_converter)
```

### Adding New Configuration

Edit `config/settings.py`:

```python
# Add new setting
MY_NEW_SETTING = "value"
```

Access from any module:

```python
from config.settings import MY_NEW_SETTING
```

## Testing

### Unit Testing Example

```python
import unittest
from src.converters.libreoffice_converter import LibreOfficeConverter

class TestLibreOfficeConverter(unittest.TestCase):
    def setUp(self):
        self.converter = LibreOfficeConverter()
    
    def test_availability(self):
        # Test if LibreOffice is available
        available = self.converter.is_available()
        self.assertIsInstance(available, bool)
```

### Integration Testing

```python
from src.document_converter import DocumentConverter
import tempfile
from pathlib import Path

# Create temporary directories
with tempfile.TemporaryDirectory() as tmpdir:
    input_dir = Path(tmpdir) / "input"
    output_dir = Path(tmpdir) / "output"
    
    # Test conversion
    converter = DocumentConverter(str(input_dir), str(output_dir))
    stats = converter.convert_all()
```

## Performance Optimization

### Current Implementation
- Sequential processing (one file at a time)
- Suitable for small to medium batches

### Future Enhancements
- Parallel processing using multiprocessing
- Async I/O for file operations
- Progress callbacks

## Error Handling

### Graceful Degradation
- If primary converter fails, tries next converter
- Detailed error logging
- Continues processing remaining files

### Error Recovery
- Individual file failures don't stop batch processing
- Failed files are tracked in statistics
- Detailed error messages in log files

## Configuration Options

### Environment Variables (Future)
```bash
export DOC_CONVERTER_INPUT=/path/to/input
export DOC_CONVERTER_OUTPUT=/path/to/output
export DOC_CONVERTER_TIMEOUT=120
```

### Configuration File (Future)
```yaml
# config.yaml
input_dir: ./input
output_dir: ./output
timeout: 120
converters:
  - libreoffice
  - ms_office
  - python
```

## Best Practices Implemented

1. **DRY (Don't Repeat Yourself)**
   - Shared utilities in utils package
   - Reusable converter interface

2. **SOLID Principles**
   - Single Responsibility: Each class has one purpose
   - Open/Closed: Easy to extend, hard to modify
   - Liskov Substitution: Converters are interchangeable
   - Interface Segregation: Minimal interfaces
   - Dependency Inversion: Depend on abstractions

3. **Clean Code**
   - Descriptive names
   - Type hints
   - Comprehensive docstrings
   - Consistent formatting

4. **Pythonic**
   - Use of pathlib for paths
   - Context managers where appropriate
   - List comprehensions
   - Type annotations

## Migration from v1.0

Old code:
```python
converter = DocumentConverter("./docs", "./pdfs")
```

New code (same API):
```python
converter = DocumentConverter("./docs", "./pdfs")
# Or use defaults:
converter = DocumentConverter()  # Uses ./input and ./output
```

## Troubleshooting

### Import Errors
- Ensure you're running from the data_converter directory
- Check PYTHONPATH includes the project root

### Converter Not Found
- Check converter availability: `converter.converter_factory.get_available_converters_info()`
- Install missing dependencies

### Permission Errors
- Ensure write permissions for output directory
- Close files in other applications

## Future Roadmap

- [ ] Parallel processing
- [ ] Web interface
- [ ] REST API
- [ ] Docker container
- [ ] Cloud storage integration
- [ ] Batch configuration files
- [ ] Progress bars with tqdm
- [ ] Email notifications
- [ ] Webhook support

---

**Version**: 2.0
**Python**: 3.7+
**Author**: AI4Team
**License**: See LICENSE file
