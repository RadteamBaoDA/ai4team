"""
Microsoft Office converter implementation
"""

import subprocess
import platform
import gc
from pathlib import Path
from threading import Lock
from .base_converter import BaseConverter
from ..utils import setup_logger
from config.settings import (
    MS_OFFICE_PATHS,
    CONVERSION_TIMEOUT,
    EXCEL_FORCE_SINGLE_PAGE,
    EXCEL_AUTO_LANDSCAPE,
    EXCEL_LIMIT_PRINT_AREA,
    EXCEL_SINGLE_PAGE_THRESHOLD,
    EXCEL_MARGIN_INCHES,
    EXCEL_HEADER_MARGIN_INCHES,
    MEMORY_OPTIMIZATION,
)


# Global lock for PowerPoint COM automation (not thread-safe in parallel)
_powerpoint_lock = Lock()


# Excel COM constants (avoids importing win32com generated constants)
XL_ORIENT_PORTRAIT = 1
XL_ORIENT_LANDSCAPE = 2
XL_FIND_LOOKIN_VALUES = -4163
XL_FIND_SEARCHORDER_ROWS = 1
XL_FIND_DIRECTION_NEXT = 1
XL_FIND_DIRECTION_PREV = 2


class MSOfficeConverter(BaseConverter):
    """Converts documents using Microsoft Office"""
    
    def __init__(self):
        self.logger = setup_logger(__name__)
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
                # Use DispatchEx to force a new instance for better isolation
                word = win32com.client.DispatchEx("Word.Application")
                word.Visible = False
                word.ScreenUpdating = False
                
                doc = word.Documents.Open(str(input_file.resolve()))
                
                # Set encoding to UTF-8 to fix font/encoding issues
                try:
                    doc.WebOptions.Encoding = 65001
                except:
                    pass

                # Try to set embedding option
                try:
                    doc.EmbedTrueTypeFonts = True
                except:
                    pass

                # Use ExportAsFixedFormat instead of SaveAs for better PDF control
                # 17 = wdExportFormatPDF
                doc.ExportAsFixedFormat(
                    OutputFileName=str(output_file.resolve()),
                    ExportFormat=17,
                    OpenAfterExport=False,
                    OptimizeFor=0, # wdExportOptimizeForPrint
                    Range=0, # wdExportAllDocument
                    Item=0, # wdExportDocumentContent
                    IncludeDocProps=True,
                    KeepIRM=True,
                    CreateBookmarks=1, # wdExportCreateHeadingBookmarks
                    DocStructureTags=True,
                    BitmapMissingFonts=True,
                    UseISO19005_1=True # PDF/A compliant (forces font embedding)
                )
                
                doc.Close(SaveChanges=False)
                del doc
                doc = None
                
                word.Quit()
                del word
                word = None
                
                if MEMORY_OPTIMIZATION:
                    gc.collect()

                return True
                
            except Exception:
                # Cleanup on error
                if doc:
                    try:
                        doc.Close(SaveChanges=False)
                    except:
                        pass
                    del doc
                if word:
                    try:
                        word.Quit()
                    except:
                        pass
                    del word
                if MEMORY_OPTIMIZATION:
                    gc.collect()
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
                # Use DispatchEx to force a new instance for better isolation
                excel = win32com.client.DispatchEx("Excel.Application")
                excel.Visible = False
                excel.DisplayAlerts = False
                excel.ScreenUpdating = False
                
                workbook = excel.Workbooks.Open(str(input_file.resolve()))
                
                # Set encoding to UTF-8
                try:
                    workbook.WebOptions.Encoding = 65001
                except:
                    pass

                # Force worksheets to a consistent layout before exporting
                margin = excel.Application.InchesToPoints(EXCEL_MARGIN_INCHES)
                header_margin = excel.Application.InchesToPoints(EXCEL_HEADER_MARGIN_INCHES)
                sheet_count = workbook.Worksheets.Count
                for idx in range(1, sheet_count + 1):
                    sheet = workbook.Worksheets(idx)
                    try:
                        self._prepare_excel_sheet(
                            sheet,
                            margin,
                            header_margin,
                        )
                    except Exception as prep_error:
                        # Keep conversions resilient while surfacing diagnostics for troubleshooting
                        self.logger.debug(
                            "Excel page setup failed for %s: %s",
                            getattr(sheet, "Name", "<unknown>"),
                            prep_error,
                        )
                
                # 0 = xlTypePDF
                # 0 = xlQualityStandard
                workbook.ExportAsFixedFormat(
                    Type=0, 
                    Filename=str(output_file.resolve()),
                    Quality=0,
                    IncludeDocProperties=True,
                    IgnorePrintAreas=False,
                    OpenAfterPublish=False
                )
                
                workbook.Close(SaveChanges=False)
                del workbook
                workbook = None
                
                excel.Quit()
                del excel
                excel = None
                
                if MEMORY_OPTIMIZATION:
                    gc.collect()

                return True
                
            except Exception:
                # Cleanup on error
                if workbook:
                    try:
                        workbook.Close(SaveChanges=False)
                    except:
                        pass
                    del workbook
                if excel:
                    try:
                        excel.Quit()
                    except:
                        pass
                    del excel
                if MEMORY_OPTIMIZATION:
                    gc.collect()
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

    def _prepare_excel_sheet(self, sheet, margin_pts: float, header_margin_pts: float) -> None:
        """Apply layout rules so PDF output is consistent and legible."""
        bounds = self._get_sheet_bounds(sheet) if EXCEL_LIMIT_PRINT_AREA or EXCEL_FORCE_SINGLE_PAGE or EXCEL_AUTO_LANDSCAPE else None

        if EXCEL_LIMIT_PRINT_AREA and bounds:
            first_row, first_col, last_row, last_col = bounds
            try:
                address = sheet.Range(
                    sheet.Cells(first_row, first_col),
                    sheet.Cells(last_row, last_col)
                ).Address
                sheet.PageSetup.PrintArea = address
            except Exception as print_error:
                self.logger.debug(
                    "Could not restrict print area for %s: %s",
                    getattr(sheet, "Name", "<unknown>"),
                    print_error,
                )

        column_count, row_count = (0, 0)
        if bounds:
            first_row, first_col, last_row, last_col = bounds
            column_count = max(1, last_col - first_col + 1)
            row_count = max(1, last_row - first_row + 1)

        # Optional orientation adjustment
        if EXCEL_AUTO_LANDSCAPE and bounds:
            try:
                orientation = XL_ORIENT_LANDSCAPE if column_count > row_count else XL_ORIENT_PORTRAIT
                sheet.PageSetup.Orientation = orientation
            except Exception as orientation_error:
                self.logger.debug(
                    "Orientation adjustment failed for %s: %s",
                    getattr(sheet, "Name", "<unknown>"),
                    orientation_error,
                )

        # Decide whether to force single page
        should_force_single_page = EXCEL_FORCE_SINGLE_PAGE and (
            not bounds or column_count > EXCEL_SINGLE_PAGE_THRESHOLD or row_count > EXCEL_SINGLE_PAGE_THRESHOLD
        )

        try:
            if should_force_single_page:
                sheet.PageSetup.Zoom = False
                sheet.PageSetup.FitToPagesWide = 1
                sheet.PageSetup.FitToPagesTall = 1
            else:
                sheet.PageSetup.Zoom = True
        except Exception as sizing_error:
            self.logger.debug(
                "Scaling adjustment failed for %s: %s",
                getattr(sheet, "Name", "<unknown>"),
                sizing_error,
            )

        # Apply consistent margins regardless of layout logic
        try:
            sheet.PageSetup.LeftMargin = margin_pts
            sheet.PageSetup.RightMargin = margin_pts
            sheet.PageSetup.TopMargin = margin_pts
            sheet.PageSetup.BottomMargin = margin_pts
            sheet.PageSetup.HeaderMargin = header_margin_pts
            sheet.PageSetup.FooterMargin = header_margin_pts
        except Exception as margin_error:
            self.logger.debug(
                "Margin adjustment failed for %s: %s",
                getattr(sheet, "Name", "<unknown>"),
                margin_error,
            )

    def _get_sheet_bounds(self, sheet):
        """Return the rectangle (first_row, first_col, last_row, last_col) containing real data."""
        try:
            cells = sheet.Cells
            last_cell = cells.Find(
                "*",
                LookIn=XL_FIND_LOOKIN_VALUES,
                SearchOrder=XL_FIND_SEARCHORDER_ROWS,
                SearchDirection=XL_FIND_DIRECTION_PREV,
            )
            if not last_cell:
                return None

            first_cell = cells.Find(
                "*",
                LookIn=XL_FIND_LOOKIN_VALUES,
                SearchOrder=XL_FIND_SEARCHORDER_ROWS,
                SearchDirection=XL_FIND_DIRECTION_NEXT,
            )
            if not first_cell:
                first_cell = last_cell

            return (
                int(first_cell.Row),
                int(first_cell.Column),
                int(last_cell.Row),
                int(last_cell.Column),
            )
        except Exception as bounds_error:
            self.logger.debug(
                "Failed to detect data bounds for %s: %s",
                getattr(sheet, "Name", "<unknown>"),
                bounds_error,
            )
            return None
    
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
                    # Use DispatchEx to force a new instance for better isolation
                    powerpoint = win32com.client.DispatchEx("PowerPoint.Application")
                    
                    # Open presentation with minimal settings
                    presentation = powerpoint.Presentations.Open(
                        str(input_file.resolve()),
                        ReadOnly=1,  # Read-only
                        Untitled=0,  # Not untitled
                        WithWindow=0  # No window
                    )
                    
                    # Save as PDF (format 32 = ppSaveAsPDF)
                    # Third arg is EmbedTrueTypeFonts (-1 = msoTrue)
                    presentation.SaveAs(str(output_file.resolve()), 32, -1)
                    presentation.Close()
                    del presentation
                    presentation = None
                    
                    powerpoint.Quit()
                    del powerpoint
                    powerpoint = None
                    
                    if MEMORY_OPTIMIZATION:
                        gc.collect()

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
                        del presentation
                    if powerpoint:
                        try:
                            powerpoint.Quit()
                        except:
                            pass
                        del powerpoint
                    if MEMORY_OPTIMIZATION:
                        gc.collect()
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
