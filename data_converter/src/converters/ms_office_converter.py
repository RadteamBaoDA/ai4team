"""
Microsoft Office converter implementation
"""

import subprocess
import platform
from pathlib import Path
from .base_converter import BaseConverter
from config.settings import MS_OFFICE_PATHS, CONVERSION_TIMEOUT


class MSOfficeConverter(BaseConverter):
    """Converts documents using Microsoft Office"""
    
    def __init__(self):
        self._word_path = None
        self._excel_path = None
        self._powerpoint_path = None
        self._check_availability()
    
    def _check_availability(self):
        """Check which MS Office applications are available"""
        if platform.system() != 'Windows':
            return
        
        # Check Word
        for path in MS_OFFICE_PATHS['word']:
            if Path(path).exists():
                self._word_path = path
                break
        
        # Check Excel
        for path in MS_OFFICE_PATHS['excel']:
            if Path(path).exists():
                self._excel_path = path
                break
        
        # Check PowerPoint
        for path in MS_OFFICE_PATHS['powerpoint']:
            if Path(path).exists():
                self._powerpoint_path = path
                break
    
    def is_available(self) -> bool:
        """Check if any MS Office application is available"""
        return any([self._word_path, self._excel_path, self._powerpoint_path])
    
    def _convert_with_word(self, input_file: Path, output_file: Path) -> bool:
        """Convert DOCX using MS Word"""
        if not self._word_path:
            return False
        
        try:
            import win32com.client
            
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            
            try:
                doc = word.Documents.Open(str(input_file.resolve()))
                doc.SaveAs(str(output_file.resolve()), FileFormat=17)  # 17 = wdFormatPDF
                doc.Close()
                return True
            finally:
                word.Quit()
                
        except Exception:
            return False
    
    def _convert_with_excel(self, input_file: Path, output_file: Path) -> bool:
        """Convert XLSX using MS Excel"""
        if not self._excel_path:
            return False
        
        try:
            import win32com.client
            
            excel = win32com.client.Dispatch("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            
            try:
                workbook = excel.Workbooks.Open(str(input_file.resolve()))
                workbook.ExportAsFixedFormat(0, str(output_file.resolve()))  # 0 = xlTypePDF
                workbook.Close(SaveChanges=False)
                return True
            finally:
                excel.Quit()
                
        except Exception:
            return False
    
    def _convert_with_powerpoint(self, input_file: Path, output_file: Path) -> bool:
        """Convert PPTX using MS PowerPoint"""
        if not self._powerpoint_path:
            return False
        
        try:
            import win32com.client
            
            powerpoint = win32com.client.Dispatch("PowerPoint.Application")
            powerpoint.Visible = True  # PowerPoint requires visible window
            
            try:
                presentation = powerpoint.Presentations.Open(str(input_file.resolve()))
                presentation.SaveAs(str(output_file.resolve()), 32)  # 32 = ppSaveAsPDF
                presentation.Close()
                return True
            finally:
                powerpoint.Quit()
                
        except Exception:
            return False
    
    def convert(self, input_file: Path, output_file: Path) -> bool:
        """
        Convert document using Microsoft Office
        
        Args:
            input_file: Source file
            output_file: Destination PDF file
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False
        
        ext = input_file.suffix.lower()
        
        try:
            if ext in {'.docx', '.doc'}:
                return self._convert_with_word(input_file, output_file)
            elif ext in {'.xlsx', '.xls'}:
                return self._convert_with_excel(input_file, output_file)
            elif ext in {'.pptx', '.ppt'}:
                return self._convert_with_powerpoint(input_file, output_file)
            
            return False
            
        except Exception:
            return False
