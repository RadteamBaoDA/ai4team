"""
Microsoft Office converter implementation
"""

import subprocess
import platform
from pathlib import Path
from threading import Lock
from .base_converter import BaseConverter
from config.settings import MS_OFFICE_PATHS, CONVERSION_TIMEOUT


# Global lock for PowerPoint COM automation (not thread-safe in parallel)
_powerpoint_lock = Lock()


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
            import pythoncom
            
            # Initialize COM for this thread (required for multi-threading)
            pythoncom.CoInitialize()
            
            word = None
            doc = None
            
            try:
                word = win32com.client.Dispatch("Word.Application")
                word.Visible = False
                
                doc = word.Documents.Open(str(input_file.resolve()))
                doc.SaveAs(str(output_file.resolve()), FileFormat=17)  # 17 = wdFormatPDF
                doc.Close()
                doc = None
                
                word.Quit()
                word = None
                
                return True
                
            except Exception:
                # Cleanup on error
                if doc:
                    try:
                        doc.Close(SaveChanges=False)
                    except:
                        pass
                if word:
                    try:
                        word.Quit()
                    except:
                        pass
                raise
                
        except ImportError:
            return False
        except Exception:
            return False
        finally:
            # Uninitialize COM for this thread
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except:
                pass
    
    def _convert_with_excel(self, input_file: Path, output_file: Path) -> bool:
        """Convert XLSX using MS Excel"""
        if not self._excel_path:
            return False
        
        try:
            import win32com.client
            import pythoncom
            
            # Initialize COM for this thread (required for multi-threading)
            pythoncom.CoInitialize()
            
            excel = None
            workbook = None
            
            try:
                excel = win32com.client.Dispatch("Excel.Application")
                excel.Visible = False
                excel.DisplayAlerts = False
                
                workbook = excel.Workbooks.Open(str(input_file.resolve()))
                workbook.ExportAsFixedFormat(0, str(output_file.resolve()))  # 0 = xlTypePDF
                workbook.Close(SaveChanges=False)
                workbook = None
                
                excel.Quit()
                excel = None
                
                return True
                
            except Exception:
                # Cleanup on error
                if workbook:
                    try:
                        workbook.Close(SaveChanges=False)
                    except:
                        pass
                if excel:
                    try:
                        excel.Quit()
                    except:
                        pass
                raise
                
        except ImportError:
            return False
        except Exception:
            return False
        finally:
            # Uninitialize COM for this thread
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except:
                pass
    
    def _convert_with_powerpoint(self, input_file: Path, output_file: Path) -> bool:
        """Convert PPTX using MS PowerPoint (serialized with lock for thread safety)"""
        if not self._powerpoint_path:
            return False
        
        # PowerPoint COM automation is not thread-safe, use lock to serialize
        with _powerpoint_lock:
            try:
                import win32com.client
                import pywintypes
                import pythoncom
                
                # Initialize COM for this thread (required for multi-threading)
                pythoncom.CoInitialize()
                
                powerpoint = None
                presentation = None
                
                try:
                    # Create PowerPoint application
                    powerpoint = win32com.client.Dispatch("PowerPoint.Application")
                    
                    # Open presentation with minimal settings
                    presentation = powerpoint.Presentations.Open(
                        str(input_file.resolve()),
                        ReadOnly=1,  # Read-only
                        Untitled=0,  # Not untitled
                        WithWindow=0  # No window
                    )
                    
                    # Save as PDF (format 32 = ppSaveAsPDF)
                    presentation.SaveAs(str(output_file.resolve()), 32)
                    presentation.Close()
                    presentation = None
                    
                    powerpoint.Quit()
                    powerpoint = None
                    
                    # Brief delay to let PowerPoint fully terminate before next thread
                    import time
                    time.sleep(0.2)
                    
                    return True
                    
                except Exception as e:
                    # Cleanup on any error
                    if presentation:
                        try:
                            presentation.Close()
                        except:
                            pass
                    if powerpoint:
                        try:
                            powerpoint.Quit()
                        except:
                            pass
                    # Re-raise to be caught by outer exception handler
                    raise
                    
            except ImportError:
                # win32com not available
                return False
            except Exception:
                return False
            finally:
                # Uninitialize COM for this thread
                try:
                    import pythoncom
                    pythoncom.CoUninitialize()
                except:
                    pass
    
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
