"""
PDF Parser optimized for RAG systems.
Extracts text, tables, images, and structural elements with metadata for citations.
"""

import os
import re
import base64
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ContentType(Enum):
    """Types of content that can be extracted from a PDF."""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    FIGURE = "figure"
    CHART = "chart"
    HEADER = "header"
    FOOTER = "footer"
    LIST = "list"
    CODE = "code"


@dataclass
class BoundingBox:
    """Represents a bounding box for visual elements."""
    x0: float
    y0: float
    x1: float
    y1: float
    page: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "x0": self.x0,
            "y0": self.y0,
            "x1": self.x1,
            "y1": self.y1,
            "page": self.page
        }


@dataclass
class ContentBlock:
    """Represents a block of content extracted from a PDF."""
    content_type: ContentType
    content: str  # Text content or base64 encoded image
    page_number: int
    bbox: Optional[BoundingBox] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # For tables
    table_data: Optional[List[List[str]]] = None
    table_headers: Optional[List[str]] = None
    
    # For images/figures/charts
    image_data: Optional[bytes] = None
    image_format: Optional[str] = None
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    
    # For citations
    section_title: Optional[str] = None
    paragraph_index: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": self.content_type.value,
            "content": self.content,
            "page": self.page_number,
            "metadata": self.metadata,
            "section": self.section_title,
            "paragraph_idx": self.paragraph_index,
        }
        if self.bbox:
            result["bbox"] = self.bbox.to_dict()
        if self.table_data:
            result["table_data"] = self.table_data
            result["table_headers"] = self.table_headers
        if self.image_data:
            result["image_base64"] = base64.b64encode(self.image_data).decode('utf-8')
            result["image_format"] = self.image_format
        if self.caption:
            result["caption"] = self.caption
        if self.alt_text:
            result["alt_text"] = self.alt_text
        return result
    
    def get_embedding_text(self) -> str:
        """Get text suitable for embedding generation."""
        parts = []
        
        # Add section context
        if self.section_title:
            parts.append(f"[Section: {self.section_title}]")
        
        if self.content_type == ContentType.TABLE:
            # Format table for embedding
            if self.table_headers:
                parts.append("Table columns: " + ", ".join(self.table_headers))
            if self.table_data:
                # Include first few rows as context
                for row in self.table_data[:5]:
                    parts.append(" | ".join(str(cell) for cell in row))
                if len(self.table_data) > 5:
                    parts.append(f"... and {len(self.table_data) - 5} more rows")
        elif self.content_type in (ContentType.IMAGE, ContentType.FIGURE, ContentType.CHART):
            # Use caption and alt text for images
            if self.caption:
                parts.append(f"Figure: {self.caption}")
            if self.alt_text:
                parts.append(f"Description: {self.alt_text}")
            parts.append(self.content)  # OCR text if available
        else:
            parts.append(self.content)
        
        return "\n".join(parts)


@dataclass 
class PDFDocument:
    """Represents a parsed PDF document."""
    source_path: str
    filename: str
    total_pages: int
    blocks: List[ContentBlock] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_path,
            "filename": self.filename,
            "total_pages": self.total_pages,
            "metadata": self.metadata,
            "blocks": [b.to_dict() for b in self.blocks]
        }


class PDFParser:
    """
    Advanced PDF parser optimized for RAG systems.
    
    Features:
    - Extracts text with structural awareness (headers, paragraphs, lists)
    - Extracts tables with headers and data
    - Extracts images/figures/charts with captions
    - Preserves bounding boxes for visual citation
    - Generates embedding-friendly text
    """
    
    def __init__(
        self,
        extract_images: bool = True,
        extract_tables: bool = True,
        ocr_images: bool = False,
        detect_headers: bool = True,
        min_image_size: int = 100,  # Minimum dimension in pixels
        image_format: str = "png",
    ):
        self.extract_images = extract_images
        self.extract_tables = extract_tables
        self.ocr_images = ocr_images
        self.detect_headers = detect_headers
        self.min_image_size = min_image_size
        self.image_format = image_format
        
        # Try to import PDF libraries
        self._pdfplumber = None
        self._fitz = None  # PyMuPDF
        self._pdf2image = None
        self._pytesseract = None
        
        self._init_libraries()
    
    def _init_libraries(self):
        """Initialize available PDF processing libraries."""
        try:
            import pdfplumber
            self._pdfplumber = pdfplumber
        except ImportError:
            pass
        
        try:
            import fitz  # PyMuPDF
            self._fitz = fitz
        except ImportError:
            pass
        
        if self.ocr_images:
            try:
                import pytesseract
                self._pytesseract = pytesseract
            except ImportError:
                pass
    
    def parse(self, pdf_path: str) -> PDFDocument:
        """
        Parse a PDF file and extract all content blocks.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            PDFDocument with extracted content
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        # Use PyMuPDF if available (faster and more features)
        if self._fitz:
            return self._parse_with_pymupdf(pdf_path)
        elif self._pdfplumber:
            return self._parse_with_pdfplumber(pdf_path)
        else:
            raise ImportError("No PDF library available. Install pymupdf or pdfplumber.")
    
    def _parse_with_pymupdf(self, pdf_path: Path) -> PDFDocument:
        """Parse PDF using PyMuPDF (fitz)."""
        doc = self._fitz.open(str(pdf_path))
        
        blocks: List[ContentBlock] = []
        current_section = None
        paragraph_idx = 0
        
        # Extract document metadata
        metadata = {
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "creator": doc.metadata.get("creator", ""),
            "creation_date": doc.metadata.get("creationDate", ""),
        }
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_blocks = page.get_text("dict", flags=self._fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
            
            for block in page_blocks:
                if block["type"] == 0:  # Text block
                    text_block = self._process_text_block(
                        block, page_num + 1, current_section, paragraph_idx
                    )
                    if text_block:
                        # Check if this is a header
                        if text_block.content_type == ContentType.HEADER:
                            current_section = text_block.content
                            paragraph_idx = 0
                        else:
                            paragraph_idx += 1
                        blocks.append(text_block)
                        
                elif block["type"] == 1 and self.extract_images:  # Image block
                    image_block = self._process_image_block(
                        block, page, page_num + 1, current_section
                    )
                    if image_block:
                        blocks.append(image_block)
            
            # Extract tables separately using pdfplumber if available
            if self.extract_tables and self._pdfplumber:
                table_blocks = self._extract_tables_from_page(
                    pdf_path, page_num, current_section
                )
                blocks.extend(table_blocks)
        
        doc.close()
        
        return PDFDocument(
            source_path=str(pdf_path),
            filename=pdf_path.name,
            total_pages=len(doc),
            blocks=blocks,
            metadata=metadata
        )
    
    def _process_text_block(
        self, 
        block: Dict, 
        page_num: int,
        current_section: Optional[str],
        paragraph_idx: int
    ) -> Optional[ContentBlock]:
        """Process a text block from PyMuPDF."""
        lines = block.get("lines", [])
        if not lines:
            return None
        
        # Extract text and analyze font sizes
        text_parts = []
        font_sizes = []
        
        for line in lines:
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if text:
                    text_parts.append(text)
                    font_sizes.append(span.get("size", 12))
        
        if not text_parts:
            return None
        
        full_text = " ".join(text_parts)
        avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 12
        
        # Detect content type based on font size and formatting
        content_type = ContentType.TEXT
        if self.detect_headers and avg_font_size > 14:
            content_type = ContentType.HEADER
        elif self._is_list_item(full_text):
            content_type = ContentType.LIST
        elif self._is_code_block(full_text):
            content_type = ContentType.CODE
        
        bbox = BoundingBox(
            x0=block["bbox"][0],
            y0=block["bbox"][1],
            x1=block["bbox"][2],
            y1=block["bbox"][3],
            page=page_num
        )
        
        return ContentBlock(
            content_type=content_type,
            content=full_text,
            page_number=page_num,
            bbox=bbox,
            section_title=current_section,
            paragraph_index=paragraph_idx,
            metadata={"font_size": avg_font_size}
        )
    
    def _process_image_block(
        self,
        block: Dict,
        page,
        page_num: int,
        current_section: Optional[str]
    ) -> Optional[ContentBlock]:
        """Process an image block from PyMuPDF."""
        try:
            # Get image dimensions
            width = block["width"]
            height = block["height"]
            
            # Skip small images (likely icons/decorations)
            if width < self.min_image_size or height < self.min_image_size:
                return None
            
            # Extract image
            xref = block.get("image")
            if not xref:
                return None
            
            # Get image data
            base_image = page.parent.extract_image(xref)
            if not base_image:
                return None
            
            image_data = base_image["image"]
            image_ext = base_image["ext"]
            
            # Determine if this is likely a chart/figure
            content_type = ContentType.IMAGE
            # Heuristic: charts are often wider than tall, figures have captions nearby
            if width > height * 1.5:
                content_type = ContentType.CHART
            elif width > 200 and height > 200:
                content_type = ContentType.FIGURE
            
            bbox = BoundingBox(
                x0=block["bbox"][0],
                y0=block["bbox"][1],
                x1=block["bbox"][2],
                y1=block["bbox"][3],
                page=page_num
            )
            
            # OCR the image if enabled
            ocr_text = ""
            if self.ocr_images and self._pytesseract:
                try:
                    from PIL import Image
                    import io
                    img = Image.open(io.BytesIO(image_data))
                    ocr_text = self._pytesseract.image_to_string(img)
                except Exception:
                    pass
            
            # Generate alt text based on image analysis
            alt_text = self._generate_alt_text(image_data, content_type)
            
            return ContentBlock(
                content_type=content_type,
                content=ocr_text,
                page_number=page_num,
                bbox=bbox,
                image_data=image_data,
                image_format=image_ext,
                alt_text=alt_text,
                section_title=current_section,
                metadata={"width": width, "height": height}
            )
            
        except Exception:
            return None
    
    def _extract_tables_from_page(
        self,
        pdf_path: Path,
        page_num: int,
        current_section: Optional[str]
    ) -> List[ContentBlock]:
        """Extract tables from a page using pdfplumber."""
        blocks = []
        
        try:
            with self._pdfplumber.open(str(pdf_path)) as pdf:
                if page_num >= len(pdf.pages):
                    return blocks
                    
                page = pdf.pages[page_num]
                tables = page.extract_tables()
                
                for table_idx, table in enumerate(tables):
                    if not table or len(table) < 2:
                        continue
                    
                    # First row as headers
                    headers = [str(cell) if cell else "" for cell in table[0]]
                    data = [[str(cell) if cell else "" for cell in row] for row in table[1:]]
                    
                    # Generate text representation
                    text_repr = self._table_to_text(headers, data)
                    
                    blocks.append(ContentBlock(
                        content_type=ContentType.TABLE,
                        content=text_repr,
                        page_number=page_num + 1,
                        table_data=data,
                        table_headers=headers,
                        section_title=current_section,
                        paragraph_index=table_idx,
                        metadata={"rows": len(data), "cols": len(headers)}
                    ))
                    
        except Exception:
            pass
        
        return blocks
    
    def _parse_with_pdfplumber(self, pdf_path: Path) -> PDFDocument:
        """Parse PDF using pdfplumber (fallback)."""
        blocks: List[ContentBlock] = []
        current_section = None
        
        with self._pdfplumber.open(str(pdf_path)) as pdf:
            metadata = pdf.metadata or {}
            
            for page_num, page in enumerate(pdf.pages):
                # Extract text
                text = page.extract_text() or ""
                if text.strip():
                    # Simple paragraph splitting
                    paragraphs = text.split("\n\n")
                    for para_idx, para in enumerate(paragraphs):
                        para = para.strip()
                        if not para:
                            continue
                        
                        # Detect headers (simplified)
                        content_type = ContentType.TEXT
                        if len(para) < 100 and para.isupper():
                            content_type = ContentType.HEADER
                            current_section = para
                        
                        blocks.append(ContentBlock(
                            content_type=content_type,
                            content=para,
                            page_number=page_num + 1,
                            section_title=current_section,
                            paragraph_index=para_idx
                        ))
                
                # Extract tables
                if self.extract_tables:
                    table_blocks = self._extract_tables_from_page(
                        pdf_path, page_num, current_section
                    )
                    blocks.extend(table_blocks)
        
        return PDFDocument(
            source_path=str(pdf_path),
            filename=pdf_path.name,
            total_pages=len(pdf.pages),
            blocks=blocks,
            metadata=metadata
        )
    
    def _is_list_item(self, text: str) -> bool:
        """Check if text is a list item."""
        patterns = [
            r"^\s*[\•\-\*\◦\▪]\s+",  # Bullet points
            r"^\s*\d+[\.\)]\s+",      # Numbered lists
            r"^\s*[a-zA-Z][\.\)]\s+", # Lettered lists
        ]
        return any(re.match(p, text) for p in patterns)
    
    def _is_code_block(self, text: str) -> bool:
        """Check if text looks like code."""
        code_indicators = [
            "def ", "class ", "import ", "from ", "return ",
            "function ", "const ", "let ", "var ",
            "{", "}", "=>", "->",
        ]
        return any(ind in text for ind in code_indicators)
    
    def _table_to_text(self, headers: List[str], data: List[List[str]]) -> str:
        """Convert table to text representation."""
        lines = []
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "|".join(["---" for _ in headers]) + "|")
        for row in data:
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)
    
    def _generate_alt_text(self, image_data: bytes, content_type: ContentType) -> str:
        """Generate alt text for an image (placeholder for vision model integration)."""
        # This is a placeholder - in production, you'd use a vision model
        img_hash = hashlib.md5(image_data).hexdigest()[:8]
        type_name = content_type.value
        return f"[{type_name.capitalize()} {img_hash}]"
