"""
Converter factory and manager
"""

from pathlib import Path
from typing import List, Optional
from .base_converter import BaseConverter
from .libreoffice_converter import LibreOfficeConverter
from .ms_office_converter import MSOfficeConverter
from .docling_converter import DoclingConverter
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
        self.docling = DoclingConverter()
        self.docx_converter = DocxConverter()
        self.xlsx_converter = XlsxConverter()
        self.pptx_converter = PptxConverter()
        self.csv_converter = CsvConverter()
        
        # Define priority order
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
        from config.settings import USE_DOCLING_CONVERTER, DOCLING_PRIORITY
        
        ext = file_path.suffix.lower()
        converters = []
        
        office_like_ext = {'.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt',
                           '.odt', '.ods', '.odp', '.rtf', '.html', '.htm'}
        
        # Priority 4: Try Docling before MS Office (rarely used)
        if USE_DOCLING_CONVERTER and DOCLING_PRIORITY >= 4 and ext in office_like_ext:
            if self.docling.is_available():
                converters.append(self.docling)
        
        # Try Microsoft Office first; fall back to LibreOffice only if MS Office is unavailable
        if ext in office_like_ext:
            if self.ms_office.is_available():
                converters.append(self.ms_office)
            elif self.libreoffice.is_available():
                converters.append(self.libreoffice)
        
        # Priority 3: Try Docling before LibreOffice (when MS Office unavailable)
        if USE_DOCLING_CONVERTER and DOCLING_PRIORITY >= 3 and ext in office_like_ext:
            if self.docling.is_available() and self.docling not in converters:
                converters.append(self.docling)
        
        # Priority 2: Try Docling before Python converters (default for enhanced layout)
        if USE_DOCLING_CONVERTER and DOCLING_PRIORITY >= 2 and ext in office_like_ext:
            if self.docling.is_available() and self.docling not in converters:
                converters.append(self.docling)        # Add specific Python library converter as fallback
        if ext in {'.docx', '.doc'}:
            converters.append(self.docx_converter)
        elif ext in {'.xlsx', '.xls', '.ods'}:
            converters.append(self.xlsx_converter)
        elif ext in {'.pptx', '.ppt', '.odp'}:
            converters.append(self.pptx_converter)
        elif ext == '.csv':
            converters.append(self.csv_converter)
        
        # Priority 1: Try Docling as final fallback (least priority)
        if USE_DOCLING_CONVERTER and DOCLING_PRIORITY >= 1 and ext in office_like_ext:
            if self.docling.is_available() and self.docling not in converters:
                converters.append(self.docling)
        
        return converters
    
    def get_available_converters_info(self) -> dict:
        """
        Get information about available converters
        
        Returns:
            Dictionary with converter availability status
        """
        return {
            'Microsoft Office': self.ms_office.is_available(),
            'LibreOffice': self.libreoffice.is_available(),
            'Docling (Advanced Layout)': self.docling.is_available(),
            'Python Libraries': True
        }
