"""
Converter factory and manager
"""

from pathlib import Path
from typing import List, Optional
from .base_converter import BaseConverter
from .libreoffice_converter import LibreOfficeConverter
from .ms_office_converter import MSOfficeConverter
from .python_converters import (
    DocxConverter, 
    XlsxConverter, 
    PptxConverter,
    CsvConverter
)


class ConverterFactory:
    """Factory for creating and managing converters"""
    
    def __init__(self):
        # Initialize all converters
        self.libreoffice = LibreOfficeConverter()
        self.ms_office = MSOfficeConverter()
        self.docx_converter = DocxConverter()
        self.xlsx_converter = XlsxConverter()
        self.pptx_converter = PptxConverter()
        self.csv_converter = CsvConverter()
        
        # Define priority order with Microsoft Office first
        self._primary_converters = [
            self.ms_office,
            self.libreoffice
        ]
    
    def get_converters_for_file(self, file_path: Path) -> List[BaseConverter]:
        """
        Get list of converters for a file type in priority order
        
        Args:
            file_path: File to convert
            
        Returns:
            List of converters to try
        """
        ext = file_path.suffix.lower()
        converters = []
        
        # Try primary converters first (LibreOffice, then MS Office)
        # These handle most office formats
        if ext in {'.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', 
                   '.odt', '.ods', '.odp', '.rtf', '.html', '.htm'}:
            for converter in self._primary_converters:
                if converter.is_available():
                    converters.append(converter)
        
        # Add specific Python library converter as fallback
        if ext in {'.docx', '.doc'}:
            converters.append(self.docx_converter)
        elif ext in {'.xlsx', '.xls', '.ods'}:
            converters.append(self.xlsx_converter)
        elif ext in {'.pptx', '.ppt', '.odp'}:
            converters.append(self.pptx_converter)
        elif ext == '.csv':
            converters.append(self.csv_converter)
        
        return converters
    
    def get_available_converters_info(self) -> dict:
        """
        Get information about available converters
        
        Returns:
            Dictionary with converter availability status
        """
        return {
            'LibreOffice': self.libreoffice.is_available(),
            'Microsoft Office': self.ms_office.is_available(),
            'Python Libraries': True
        }
