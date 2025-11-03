"""
Python library-based converters (fallback methods)
"""

from pathlib import Path
from .base_converter import BaseConverter


class PythonLibraryConverter(BaseConverter):
    """Base class for Python library converters"""
    
    def is_available(self) -> bool:
        """Check if required libraries are available"""
        return True


class DocxConverter(PythonLibraryConverter):
    """Convert DOCX using docx2pdf"""
    
    def convert(self, input_file: Path, output_file: Path) -> bool:
        try:
            from docx2pdf import convert
            convert(str(input_file), str(output_file))
            return True
        except Exception:
            return False


class XlsxConverter(PythonLibraryConverter):
    """Convert XLSX using openpyxl and reportlab"""
    
    def convert(self, input_file: Path, output_file: Path) -> bool:
        try:
            from openpyxl import load_workbook
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak
            
            # Load Excel workbook
            wb = load_workbook(input_file, data_only=True)
            
            # Create PDF
            doc = SimpleDocTemplate(str(output_file), pagesize=landscape(letter))
            elements = []
            
            # Process each sheet
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                
                # Extract data
                data = []
                for row in ws.iter_rows(values_only=True):
                    row_data = [str(cell) if cell is not None else '' for cell in row]
                    data.append(row_data)
                
                if data:
                    # Create table
                    table = Table(data)
                    
                    # Style the table
                    style = TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ])
                    table.setStyle(style)
                    
                    elements.append(table)
                    elements.append(PageBreak())
            
            # Build PDF
            doc.build(elements)
            return True
            
        except Exception:
            return False


class PptxConverter(PythonLibraryConverter):
    """Convert PPTX using python-pptx and reportlab"""
    
    def convert(self, input_file: Path, output_file: Path) -> bool:
        try:
            from pptx import Presentation
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import inch
            
            # Load presentation
            prs = Presentation(input_file)
            
            # Create PDF
            c = canvas.Canvas(str(output_file), pagesize=landscape(letter))
            width, height = landscape(letter)
            
            # Process each slide
            for slide_num, slide in enumerate(prs.slides, 1):
                # Extract text from slide
                y_position = height - inch
                
                c.setFont("Helvetica-Bold", 16)
                c.drawString(inch, y_position, f"Slide {slide_num}")
                y_position -= 0.5 * inch
                
                c.setFont("Helvetica", 12)
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        text = shape.text.strip()
                        
                        # Simple text wrapping
                        for line in text.split('\n'):
                            if y_position < inch:
                                c.showPage()
                                c.setFont("Helvetica", 12)
                                y_position = height - inch
                            
                            # Truncate if too long
                            if len(line) > 100:
                                line = line[:97] + "..."
                            
                            c.drawString(inch, y_position, line)
                            y_position -= 0.3 * inch
                
                c.showPage()
            
            c.save()
            return True
            
        except Exception:
            return False


class CsvConverter(PythonLibraryConverter):
    """Convert CSV to PDF using reportlab"""
    
    def convert(self, input_file: Path, output_file: Path) -> bool:
        try:
            import csv
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
            from reportlab.lib.styles import getSampleStyleSheet
            
            # Read CSV file
            with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                data = list(reader)
            
            if not data:
                return False
            
            # Create PDF
            doc = SimpleDocTemplate(str(output_file), pagesize=landscape(letter))
            elements = []
            
            # Add title
            styles = getSampleStyleSheet()
            title = Paragraph(f"<b>{input_file.name}</b>", styles['Title'])
            elements.append(title)
            
            # Create table
            table = Table(data)
            
            # Style the table
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
            ])
            table.setStyle(style)
            
            elements.append(table)
            
            # Build PDF
            doc.build(elements)
            return True
            
        except Exception:
            return False



