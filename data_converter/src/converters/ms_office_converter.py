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
    EXCEL_PAGE_BREAK_ON_EMPTY_ROWS,
    EXCEL_PAGE_BREAK_CHAR,
    EXCEL_PRINT_ROW_COL_HEADERS,
    EXCEL_PRINT_GRIDLINES,
    EXCEL_BLACK_AND_WHITE,
    EXCEL_ADD_CITATION_HEADERS,
    EXCEL_TABLE_MAX_ROWS_PER_PAGE,
    EXCEL_TABLE_OPTIMIZATION,
    MEMORY_OPTIMIZATION,
    # Master RAG toggle
    RAG_OPTIMIZATION_ENABLED,
    # RAG Optimization Settings
    PDF_CREATE_BOOKMARKS,
    PDF_CREATE_TAGGED,
    PDF_EMBED_FONTS,
    PDF_USE_ISO19005,
    WORD_CREATE_HEADING_BOOKMARKS,
    WORD_ADD_DOC_PROPERTIES,
    WORD_PRESERVE_STRUCTURE_TAGS,
    PPTX_ADD_SLIDE_NUMBERS,
    PPTX_CREATE_OUTLINE,
    PPTX_NOTES_AS_TEXT,
    PPTX_ADD_DOC_PROPERTIES,
    CITATION_INCLUDE_DATE,
    CITATION_INCLUDE_FILENAME,
    CITATION_INCLUDE_PAGE,
    CITATION_DATE_FORMAT,
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

                # Log page count and collect document info for RAG
                page_count = 0
                try:
                    # wdStatisticPages = 2
                    page_count = doc.ComputeStatistics(2)
                    self.logger.info(f"Exporting Word document: {input_file.name} ({page_count} pages)")
                except Exception as e:
                    self.logger.debug(f"Could not get page count: {e}")
                
                # RAG Optimization: Add document metadata for better search
                try:
                    props = doc.BuiltInDocumentProperties
                    if WORD_ADD_DOC_PROPERTIES:
                        # Ensure title is set for PDF outline root
                        if not props("Title").Value:
                            props("Title").Value = input_file.stem

                        props("Subject").Value = f"Converted from: {input_file.name}"
                        props("Category").Value = "RAG Export"

                        keywords = [input_file.stem, "RAG", "Knowledge Base"]
                        if CITATION_INCLUDE_FILENAME:
                            keywords.append(input_file.name)
                        if CITATION_INCLUDE_PAGE and page_count:
                            keywords.append(f"pages:{page_count}")
                        props("Keywords").Value = ", ".join(dict.fromkeys(keywords))  # remove duplicates

                        metadata_parts = []
                        if CITATION_INCLUDE_FILENAME:
                            metadata_parts.append(f"Source: {input_file.name}")
                        if CITATION_INCLUDE_PAGE and page_count:
                            metadata_parts.append(f"Pages: {page_count}")
                        if CITATION_INCLUDE_DATE:
                            from datetime import datetime
                            metadata_parts.append(
                                f"Converted: {datetime.now().strftime(CITATION_DATE_FORMAT)}"
                            )

                        if metadata_parts:
                            props("Comments").Value = " | ".join(metadata_parts)
                except Exception as e:
                    self.logger.debug(f"Could not set document properties: {e}")
                
                # RAG Optimization: Ensure headings are properly styled for bookmark generation
                # This helps create a navigable PDF outline for KB systems
                bookmark_type = 0  # wdExportCreateNoBookmarks
                if PDF_CREATE_BOOKMARKS and WORD_CREATE_HEADING_BOOKMARKS:
                    bookmark_type = 1  # wdExportCreateHeadingBookmarks
                
                # Use ExportAsFixedFormat with RAG-optimized settings
                # 17 = wdExportFormatPDF
                doc.ExportAsFixedFormat(
                    OutputFileName=str(output_file.resolve()),
                    ExportFormat=17,
                    OpenAfterExport=False,
                    OptimizeFor=0,  # wdExportOptimizeForPrint (better quality)
                    Range=0,  # wdExportAllDocument
                    Item=0,  # wdExportDocumentContent
                    IncludeDocProps=WORD_ADD_DOC_PROPERTIES,  # Include metadata for search
                    KeepIRM=True,
                    CreateBookmarks=bookmark_type,  # PDF outline from headings
                    DocStructureTags=PDF_CREATE_TAGGED and WORD_PRESERVE_STRUCTURE_TAGS,  # Tagged PDF for parsing
                    BitmapMissingFonts=PDF_EMBED_FONTS,
                    UseISO19005_1=PDF_USE_ISO19005  # PDF/A for archival & font embedding
                )
                
                self.logger.info(f"PDF created with: bookmarks={bookmark_type==1}, tagged={PDF_CREATE_TAGGED}, PDF/A={PDF_USE_ISO19005}")
                
                self.logger.info(f"Finished exporting Word document: {input_file.name}")
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
                
                self.logger.info(f"Processing Excel workbook: {input_file.name} ({sheet_count} sheets)")

                for idx in range(1, sheet_count + 1):
                    sheet = workbook.Worksheets(idx)
                    sheet_name = getattr(sheet, "Name", f"Sheet {idx}")
                    self.logger.info(f"Preparing sheet {idx}/{sheet_count}: {sheet_name}")
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
                    IgnorePrintAreas=True,
                    OpenAfterPublish=False
                )
                
                self.logger.info(f"Finished exporting Excel workbook: {input_file.name}")
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
        
        # Constants
        XL_PAPER_A4 = 9
        XL_PAPER_A3 = 8
        XL_ORIENT_PORTRAIT = 1
        XL_ORIENT_LANDSCAPE = 2
        
        try:
            # 1. Reset Page Breaks to clean up previous print settings
            try:
                sheet.ResetAllPageBreaks()
            except:
                pass
            
            # 2. Get UsedRange and Dimensions
            used_range = sheet.UsedRange
            total_width = used_range.Width
            row_count = used_range.Rows.Count
            first_row = used_range.Row
            
            page_setup = sheet.PageSetup
            
            # 3. Page Size & Orientation Strategy
            # Adjust paper size and orientation based on content width to minimize scaling
            # A4 width ~ 595 pts (portrait), 842 pts (landscape)
            if total_width < 600: # Fits comfortably on A4 Portrait
                page_setup.PaperSize = XL_PAPER_A4
                page_setup.Orientation = XL_ORIENT_PORTRAIT
            elif total_width < 850: # Fits on A4 Landscape
                page_setup.PaperSize = XL_PAPER_A4
                page_setup.Orientation = XL_ORIENT_LANDSCAPE
            else: # Wide content, use A3 Landscape
                page_setup.PaperSize = XL_PAPER_A3
                page_setup.Orientation = XL_ORIENT_LANDSCAPE

            # 4. Fit all columns on one page width
            page_setup.Zoom = False
            page_setup.FitToPagesWide = 1
            page_setup.FitToPagesTall = False # Allow vertical scrolling for long content
            
            # Margins
            page_setup.LeftMargin = margin_pts
            page_setup.RightMargin = margin_pts
            page_setup.TopMargin = margin_pts
            page_setup.BottomMargin = margin_pts
            page_setup.HeaderMargin = header_margin_pts
            page_setup.FooterMargin = header_margin_pts
            
            # 6. RAG & Citation Optimization for Knowledge Base
            # Only apply RAG-specific features when master toggle is enabled
            if RAG_OPTIMIZATION_ENABLED and EXCEL_ADD_CITATION_HEADERS:
                # Add rich context to every page for precise citations
                # Format: [Filename] | Sheet: [SheetName] | Page X of Y | Date
                # This enables RAG systems to generate accurate citations like:
                # "Source: report.xlsx, Sheet: Sales Data, Page 3"
                
                # &F = Filename, &A = Sheet Name, &P = Page Number, &N = Total Pages, &D = Date
                # Header: Filename (center) with sheet context (right)
                page_setup.LeftHeader = ""  # Keep clean
                page_setup.CenterHeader = "&F"  # Filename prominently displayed
                page_setup.RightHeader = "[Sheet: &A]"  # Sheet context in brackets for parsing
                
                # Footer: Page info (for citation) and date (for version tracking)
                page_setup.LeftFooter = "&D"  # Date for temporal context
                page_setup.CenterFooter = "Page &P of &N"  # Standard pagination
                page_setup.RightFooter = ""  # Keep clean
                
                # RAG Tip: The format "[Sheet: X]" and "Page Y of Z" are easily
                # parseable by regex for automated citation extraction
            
            # Enable gridlines for better table structure recognition by AI/OCR models
            if RAG_OPTIMIZATION_ENABLED and EXCEL_PRINT_GRIDLINES:
                page_setup.PrintGridlines = True
            
            # Print row and column headers (A, B, C... and 1, 2, 3...) for precise cell referencing in RAG
            if RAG_OPTIMIZATION_ENABLED and EXCEL_PRINT_ROW_COL_HEADERS:
                page_setup.PrintHeadings = True
            
            # Black and white mode for better OCR and smaller file size
            if EXCEL_BLACK_AND_WHITE:
                page_setup.BlackAndWhite = True
            
            # Try to detect header rows from frozen panes to repeat them on every page
            # This ensures that data on subsequent pages retains its column context
            frozen_header_rows = 0
            if RAG_OPTIMIZATION_ENABLED:
                frozen_header_rows = self._ensure_frozen_panes_repeat_headers(sheet, page_setup)
            
            # 5. Insert Page Breaks on Empty Rows or Special Characters
            # Only process if row count is manageable to avoid performance hit
            if row_count < 20000: 
                values = used_range.Value
                # values is a tuple of tuples for 2D range, or scalar for single cell
                if isinstance(values, tuple):
                    consecutive_empty_rows = 0
                    
                    # Table detection: Check if content looks like a table
                    # Preference order: native Excel ListObjects, otherwise heuristic detection
                    is_table_content = False
                    header_row_count = 1  # Default header assumption
                    
                    if (
                        RAG_OPTIMIZATION_ENABLED
                        and EXCEL_TABLE_OPTIMIZATION
                        and EXCEL_TABLE_MAX_ROWS_PER_PAGE > 0
                    ):
                        (
                            is_table_content,
                            detected_header_rows,
                            detected_columns,
                        ) = self._detect_table_structure(sheet, values)

                        if is_table_content:
                            if frozen_header_rows:
                                header_row_count = max(detected_header_rows, frozen_header_rows)
                            else:
                                header_row_count = max(detected_header_rows, 1)

                            self.logger.info(
                                "Table detected on %s: %d rows, %d columns, %d header row(s); forcing %d rows/page",
                                getattr(sheet, "Name", "<unknown>"),
                                row_count,
                                detected_columns,
                                header_row_count,
                                EXCEL_TABLE_MAX_ROWS_PER_PAGE,
                            )
                    
                    # Track rows for table page breaks
                    data_rows_on_current_page = 0
                    
                    # Iterate to find empty rows or break chars
                    for i, row_data in enumerate(values):
                        # Skip first row (can't break before it)
                        if i == 0: continue
                        
                        is_row_empty = True
                        has_break_char = False
                        
                        # Check row content
                        for cell_val in row_data:
                            if cell_val is not None:
                                str_val = str(cell_val).strip()
                                if str_val != "":
                                    is_row_empty = False
                                    # Check for special break character
                                    if EXCEL_PAGE_BREAK_CHAR and EXCEL_PAGE_BREAK_CHAR in str_val:
                                        has_break_char = True
                                        break
                        
                        # Handle explicit page break character
                        if has_break_char:
                            current_row_num = first_row + i
                            try:
                                sheet.HPageBreaks.Add(Before=sheet.Cells(current_row_num, 1))
                                consecutive_empty_rows = 0  # Reset counter
                                data_rows_on_current_page = 0  # Reset table row counter
                                continue
                            except:
                                pass

                        # Handle empty row page breaks
                        if is_row_empty:
                            consecutive_empty_rows += 1
                        else:
                            consecutive_empty_rows = 0
                            # Count data rows for table optimization
                            if is_table_content and i >= header_row_count:
                                data_rows_on_current_page += 1
                        
                        if EXCEL_PAGE_BREAK_ON_EMPTY_ROWS > 0 and consecutive_empty_rows == EXCEL_PAGE_BREAK_ON_EMPTY_ROWS:
                            # Add page break
                            current_row_num = first_row + i
                            try:
                                sheet.HPageBreaks.Add(Before=sheet.Cells(current_row_num, 1))
                                data_rows_on_current_page = 0  # Reset table row counter
                            except:
                                pass
                        
                        # Table optimization: Add page break when max rows per page is reached
                        # Only for non-header rows in detected tables
                        if is_table_content and not is_row_empty and i >= header_row_count:
                            if data_rows_on_current_page >= EXCEL_TABLE_MAX_ROWS_PER_PAGE:
                                current_row_num = first_row + i + 1  # Break AFTER current row
                                if current_row_num <= first_row + row_count - 1:  # Don't break after last row
                                    try:
                                        sheet.HPageBreaks.Add(Before=sheet.Cells(current_row_num, 1))
                                        data_rows_on_current_page = 0  # Reset counter
                                        self.logger.debug(f"Table page break at row {current_row_num}")
                                    except:
                                        pass
                            
        except Exception as e:
            self.logger.debug(
                "Page setup failed for %s: %s",
                getattr(sheet, "Name", "<unknown>"),
                e,
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
    
    def _ensure_frozen_panes_repeat_headers(self, sheet, page_setup) -> int:
        """Set PrintTitleRows based on frozen panes and return the frozen header count."""
        try:
            sheet.Activate()
            active_window = sheet.Application.ActiveWindow
            if active_window.FreezePanes:
                split_row = int(active_window.SplitRow)
                if split_row > 0:
                    page_setup.PrintTitleRows = f"${1}:${split_row}"
                    return split_row
        except Exception as e:
            self.logger.debug(f"Failed to set PrintTitleRows: {e}")
        return 0

    def _detect_table_structure(self, sheet, values):
        """Return tuple (is_table, header_rows, column_count) for the current sheet."""
        header_rows = 1
        column_count = 0

        # Prefer explicit Excel Tables (ListObjects)
        try:
            list_objects = getattr(sheet, "ListObjects", None)
            if list_objects is not None and list_objects.Count > 0:
                table = list_objects(1)
                try:
                    header_rows = max(1, int(table.HeaderRowRange.Rows.Count))
                    column_count = int(table.HeaderRowRange.Columns.Count)
                except Exception:
                    header_rows = 1
                return True, header_rows, column_count
        except Exception as table_error:
            self.logger.debug(
                "Excel table detection failed for %s: %s",
                getattr(sheet, "Name", "<unknown>"),
                table_error,
            )

        # Fallback heuristic detection using raw values
        if not isinstance(values, tuple) or len(values) < 3:
            return False, header_rows, column_count

        try:
            first_row = values[0]
            if not isinstance(first_row, tuple):
                return False, header_rows, column_count

            header_cells = sum(1 for cell in first_row if cell is not None and str(cell).strip())
            if header_cells < 2:
                return False, header_rows, column_count

            consistent_rows = 0
            total_checked = 0

            for row_data in values[1:11]:
                if not isinstance(row_data, tuple):
                    continue
                total_checked += 1
                row_cells = sum(1 for cell in row_data if cell is not None and str(cell).strip())
                if row_cells >= header_cells * 0.5:
                    consistent_rows += 1

            if total_checked > 0 and consistent_rows / total_checked >= 0.7:
                column_count = header_cells
                return True, header_rows, column_count

            return False, header_rows, column_count

        except Exception as detection_error:
            self.logger.debug(
                "Heuristic table detection failed for %s: %s",
                getattr(sheet, "Name", "<unknown>"),
                detection_error,
            )
            return False, header_rows, column_count
    
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
                    
                    slide_count = 0
                    try:
                        slide_count = presentation.Slides.Count
                        self.logger.info(f"Exporting PowerPoint presentation: {input_file.name} ({slide_count} slides)")
                    except:
                        pass

                    if PPTX_ADD_DOC_PROPERTIES:
                        try:
                            props = presentation.BuiltInDocumentProperties
                            if not props("Title").Value:
                                props("Title").Value = input_file.stem
                            props("Subject").Value = f"Converted from: {input_file.name}"
                            keywords = [input_file.stem, "PowerPoint", "RAG"]
                            if CITATION_INCLUDE_FILENAME:
                                keywords.append(input_file.name)
                            if CITATION_INCLUDE_PAGE and slide_count:
                                keywords.append(f"slides:{slide_count}")
                            props("Keywords").Value = ", ".join(dict.fromkeys(keywords))

                            metadata_parts = []
                            if CITATION_INCLUDE_FILENAME:
                                metadata_parts.append(f"Source: {input_file.name}")
                            if CITATION_INCLUDE_PAGE and slide_count:
                                metadata_parts.append(f"Slides: {slide_count}")
                            if CITATION_INCLUDE_DATE:
                                from datetime import datetime
                                metadata_parts.append(
                                    f"Converted: {datetime.now().strftime(CITATION_DATE_FORMAT)}"
                                )
                            if metadata_parts:
                                props("Comments").Value = " | ".join(metadata_parts)
                        except Exception as e:
                            self.logger.debug(f"Could not set PowerPoint document properties: {e}")

                    if RAG_OPTIMIZATION_ENABLED and (CITATION_INCLUDE_FILENAME or CITATION_INCLUDE_DATE):
                        try:
                            footer_parts = []
                            if CITATION_INCLUDE_FILENAME:
                                footer_parts.append(f"Source: {input_file.name}")
                            if CITATION_INCLUDE_DATE:
                                from datetime import datetime
                                footer_parts.append(datetime.now().strftime(CITATION_DATE_FORMAT))
                            if footer_parts:
                                headers = presentation.SlideMaster.HeadersFooters
                                headers.Footer.Visible = True
                                headers.Footer.Text = " | ".join(footer_parts)
                        except Exception as e:
                            self.logger.debug(f"Failed to annotate slide footer: {e}")
                    
                    # RAG Optimization: Add slide numbers for citation
                    if PPTX_ADD_SLIDE_NUMBERS:
                        try:
                            # Enable slide numbers on all slides
                            for i in range(1, slide_count + 1):
                                slide = presentation.Slides(i)
                                # Try to add slide number placeholder
                                try:
                                    slide.HeadersFooters.SlideNumber.Visible = True
                                except:
                                    pass
                        except Exception as e:
                            self.logger.debug(f"Could not add slide numbers: {e}")
                    
                    # RAG Optimization: Create PDF outline from slide titles
                    # This helps KB systems navigate to specific slides
                    if PPTX_CREATE_OUTLINE:
                        try:
                            # Collect slide titles for logging
                            titles = []
                            for i in range(1, min(slide_count + 1, 10)):  # First 10 for log
                                slide = presentation.Slides(i)
                                for shape in slide.Shapes:
                                    if shape.HasTextFrame:
                                        if shape.TextFrame.HasText:
                                            title = shape.TextFrame.TextRange.Text.strip()
                                            if title and len(title) < 100:
                                                titles.append(f"Slide {i}: {title[:50]}")
                                                break
                            if titles:
                                self.logger.debug(f"Slide structure: {titles[:5]}...")
                        except:
                            pass
                    
                    # RAG Optimization: Export with notes if configured
                    # Notes often contain valuable context for search
                    if PPTX_NOTES_AS_TEXT:
                        try:
                            # ppPrintOutputNotesPages = 5 (slides with notes)
                            presentation.PrintOptions.OutputType = 5
                        except:
                            pass

                    # Save as PDF (format 32 = ppSaveAsPDF)
                    # Third arg is EmbedTrueTypeFonts (-1 = msoTrue for font embedding)
                    presentation.SaveAs(str(output_file.resolve()), 32, -1 if PDF_EMBED_FONTS else 0)
                    
                    self.logger.info(f"PowerPoint PDF created: {slide_count} slides, fonts_embedded={PDF_EMBED_FONTS}")
                    
                    self.logger.info(f"Finished exporting PowerPoint presentation: {input_file.name}")
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
