"""
Docling-enhanced converter for advanced layout recognition
Optimized for Excel files with complex table structures
"""

from pathlib import Path
from datetime import datetime
from typing import Optional

from .base_converter import BaseConverter
from ..utils import setup_logger
from config.settings import (
    CONVERSION_TIMEOUT,
    RAG_OPTIMIZATION_ENABLED,
    EXCEL_TABLE_MAX_ROWS_PER_PAGE,
    EXCEL_TABLE_OPTIMIZATION,
    EXCEL_PRINT_ROW_COL_HEADERS,
    EXCEL_PRINT_GRIDLINES,
    EXCEL_ADD_CITATION_HEADERS,
    CITATION_INCLUDE_FILENAME,
    CITATION_INCLUDE_PAGE,
    CITATION_INCLUDE_DATE,
    CITATION_DATE_FORMAT,
)


class DoclingConverter(BaseConverter):
    """
    Converts documents using Docling for enhanced layout recognition.
    
    Best for:
    - Excel files with complex tables (merged cells, borderless, rotated)
    - Multi-sheet workbooks requiring semantic understanding
    - Documents needing advanced layout analysis
    
    Requires: pip install docling reportlab pypdf
    """
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        self._docling_available = False
        self._check_availability()
    
    def _check_availability(self):
        """Check if Docling and dependencies are available"""
        try:
            import docling  # noqa: F401
            from reportlab.lib.pagesizes import letter  # noqa: F401
            self._docling_available = True
            self.logger.debug("Docling converter available")
        except ImportError as e:
            self.logger.debug(f"Docling not available: {e}")
            self._docling_available = False
    
    def is_available(self) -> bool:
        """Check if Docling converter is available"""
        return self._docling_available
    
    def convert(self, input_file: Path, output_file: Path) -> bool:
        """
        Convert document using Docling for layout analysis + ReportLab for PDF generation
        
        Args:
            input_file: Source file (Excel, Word, PowerPoint, PDF, etc.)
            output_file: Destination PDF file
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False
        
        ext = input_file.suffix.lower()
        
        # Docling supports: PDF, DOCX, PPTX, XLSX, HTML, images, audio, video
        supported_formats = {
            '.xlsx', '.xls',  # Excel
            '.docx', '.doc',  # Word
            '.pptx', '.ppt',  # PowerPoint
            '.pdf',           # PDF (re-parsing)
            '.html', '.htm',  # HTML
            '.png', '.jpg', '.jpeg', '.tiff',  # Images
        }
        
        if ext not in supported_formats:
            return False
        
        try:
            return self._convert_with_docling(input_file, output_file)
        except Exception as e:
            self.logger.error(f"Docling conversion failed for {input_file.name}: {e}")
            return False
    
    def _convert_with_docling(self, input_file: Path, output_file: Path) -> bool:
        """Convert using Docling for layout analysis"""
        try:
            from docling.document_converter import DocumentConverter
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.lib import colors
            from reportlab.platypus import (
                SimpleDocTemplate,
                Table,
                TableStyle,
                Paragraph,
                PageBreak,
                Spacer,
            )
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            
            self.logger.info(f"Converting {input_file.name} with Docling layout analysis")
            
            # Step 1: Parse document with Docling
            converter = DocumentConverter()
            result = converter.convert(str(input_file))
            doc_obj = result.document
            
            # Step 2: Create PDF with ReportLab
            pdf_doc = SimpleDocTemplate(
                str(output_file),
                pagesize=landscape(letter) if self._is_wide_content(doc_obj) else letter,
                title=input_file.stem,
            )
            elements = []
            styles = getSampleStyleSheet()
            
            # Step 3: Add citation header if RAG enabled
            if RAG_OPTIMIZATION_ENABLED and EXCEL_ADD_CITATION_HEADERS:
                citation_parts = []
                if CITATION_INCLUDE_FILENAME:
                    citation_parts.append(f"Source: {input_file.name}")
                if CITATION_INCLUDE_DATE:
                    citation_parts.append(f"Converted: {datetime.now().strftime(CITATION_DATE_FORMAT)}")
                
                if citation_parts:
                    header_text = " | ".join(citation_parts)
                    elements.append(Paragraph(f"<b>{header_text}</b>", styles['Normal']))
                    elements.append(Spacer(1, 0.2 * inch))
            
            # Step 4: Process Docling document structure
            self._process_docling_document(doc_obj, elements, styles, input_file)
            
            # Step 5: Build PDF
            pdf_doc.build(elements)
            
            # Step 6: Add metadata
            if output_file.exists():
                self._apply_pdf_metadata(output_file, input_file, doc_obj)
            
            self.logger.info(f"Successfully converted {input_file.name} with Docling")
            return True
            
        except Exception as e:
            self.logger.error(f"Docling conversion error: {e}")
            return False
    
    def _is_wide_content(self, doc_obj) -> bool:
        """Determine if document has wide content requiring landscape orientation"""
        try:
            # Check if document has tables with many columns
            for item in doc_obj.iterate_items():
                if hasattr(item, 'data') and isinstance(item.data, dict):
                    if 'num_cols' in item.data and item.data['num_cols'] > 6:
                        return True
            return False
        except:
            return False
    
    def _process_docling_document(self, doc_obj, elements, styles, input_file: Path):
        """Process Docling document structure and add to PDF elements"""
        from reportlab.platypus import Table, TableStyle, Paragraph, PageBreak
        from reportlab.lib import colors
        
        page_count = 0
        current_sheet = None
        
        # Iterate through document items
        for item in doc_obj.iterate_items():
            item_type = item.type if hasattr(item, 'type') else 'unknown'
            
            # Handle different content types
            if item_type == 'table':
                page_count += 1
                table_data = self._extract_table_data(item)
                
                if table_data:
                    # Add sheet header if new sheet
                    if hasattr(item, 'prov') and item.prov:
                        sheet_name = getattr(item.prov, 'sheet_name', None)
                        if sheet_name and sheet_name != current_sheet:
                            current_sheet = sheet_name
                            if RAG_OPTIMIZATION_ENABLED and CITATION_INCLUDE_PAGE:
                                elements.append(
                                    Paragraph(f"<b>Sheet: {sheet_name}</b>", styles['Heading2'])
                                )
                    
                    # Apply table pagination if enabled
                    if RAG_OPTIMIZATION_ENABLED and EXCEL_TABLE_OPTIMIZATION and EXCEL_TABLE_MAX_ROWS_PER_PAGE > 0:
                        self._add_paginated_table(table_data, elements, input_file)
                    else:
                        self._add_single_table(table_data, elements)
                    
            elif item_type in ('paragraph', 'text'):
                text = str(item.text) if hasattr(item, 'text') else str(item)
                if text.strip():
                    elements.append(Paragraph(text, styles['Normal']))
            
            elif item_type == 'heading':
                level = getattr(item, 'level', 1)
                style_name = f'Heading{min(level, 3)}'
                text = str(item.text) if hasattr(item, 'text') else str(item)
                elements.append(Paragraph(text, styles.get(style_name, styles['Heading1'])))
    
    def _extract_table_data(self, table_item):
        """Extract table data from Docling table item"""
        try:
            # Try to get table data from different possible attributes
            if hasattr(table_item, 'data') and isinstance(table_item.data, list):
                return table_item.data
            elif hasattr(table_item, 'cells'):
                return self._cells_to_grid(table_item.cells)
            elif hasattr(table_item, 'export_to_dataframe'):
                df = table_item.export_to_dataframe()
                return [df.columns.tolist()] + df.values.tolist()
            return None
        except Exception as e:
            self.logger.debug(f"Failed to extract table data: {e}")
            return None
    
    def _cells_to_grid(self, cells) -> list:
        """Convert cell structure to 2D grid"""
        # This is a simplified implementation
        # Real implementation would need to handle merged cells
        max_row = max(cell.row for cell in cells) + 1
        max_col = max(cell.col for cell in cells) + 1
        
        grid = [['' for _ in range(max_col)] for _ in range(max_row)]
        
        for cell in cells:
            grid[cell.row][cell.col] = str(cell.text)
        
        return grid
    
    def _add_paginated_table(self, table_data, elements, input_file: Path):
        """Add table with pagination based on EXCEL_TABLE_MAX_ROWS_PER_PAGE"""
        from reportlab.platypus import Table, TableStyle, PageBreak
        from reportlab.lib import colors
        
        if not table_data or len(table_data) < 2:
            return
        
        header = table_data[0]
        rows = table_data[1:]
        max_rows = EXCEL_TABLE_MAX_ROWS_PER_PAGE
        
        # Split into chunks
        for i in range(0, len(rows), max_rows):
            chunk = rows[i:i + max_rows]
            chunk_data = [header] + chunk
            
            table = Table(chunk_data)
            self._apply_table_style(table)
            elements.append(table)
            
            if i + max_rows < len(rows):
                elements.append(PageBreak())
    
    def _add_single_table(self, table_data, elements):
        """Add table without pagination"""
        from reportlab.platypus import Table
        
        if not table_data:
            return
        
        table = Table(table_data)
        self._apply_table_style(table)
        elements.append(table)
    
    def _apply_table_style(self, table):
        """Apply RAG-optimized table styling"""
        from reportlab.platypus import TableStyle
        from reportlab.lib import colors
        
        style_commands = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]
        
        if RAG_OPTIMIZATION_ENABLED and EXCEL_PRINT_GRIDLINES:
            style_commands.append(('GRID', (0, 0), (-1, -1), 0.5, colors.black))
        
        table.setStyle(TableStyle(style_commands))
    
    def _apply_pdf_metadata(self, pdf_path: Path, input_file: Path, doc_obj):
        """Apply PDF metadata for RAG optimization"""
        if not RAG_OPTIMIZATION_ENABLED:
            return
        
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError:
            self.logger.debug("pypdf not installed; skipping metadata")
            return
        
        try:
            reader = PdfReader(str(pdf_path))
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            
            page_count = len(reader.pages)
            metadata_parts = []
            keywords = [input_file.stem, 'Docling', 'RAG']
            
            if CITATION_INCLUDE_FILENAME:
                metadata_parts.append(f"Source: {input_file.name}")
                keywords.append(input_file.name)
            if CITATION_INCLUDE_PAGE and page_count:
                metadata_parts.append(f"Pages: {page_count}")
                keywords.append(f"pages:{page_count}")
            if CITATION_INCLUDE_DATE:
                metadata_parts.append(
                    f"Converted: {datetime.now().strftime(CITATION_DATE_FORMAT)}"
                )
            
            metadata = {
                '/Title': input_file.stem,
                '/Author': 'AI4Team Docling Converter',
                '/Subject': 'RAG Export - Enhanced Layout',
                '/Creator': 'Docling',
                '/Producer': 'ReportLab + Docling',
                '/Keywords': ', '.join(dict.fromkeys(keywords)),
            }
            if metadata_parts:
                metadata['/Comments'] = ' | '.join(metadata_parts)
            
            existing_metadata = dict(reader.metadata or {})
            existing_metadata.update(metadata)
            writer.add_metadata(existing_metadata)
            
            temp_path = pdf_path.parent / (pdf_path.name + '.tmp')
            with open(temp_path, 'wb') as f:
                writer.write(f)
            temp_path.replace(pdf_path)
            
        except Exception as e:
            self.logger.debug(f"Failed to apply metadata: {e}")
