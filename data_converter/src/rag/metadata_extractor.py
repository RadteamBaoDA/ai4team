"""
Metadata extractor for enhanced RAG search and citations.
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .pdf_parser import PDFDocument, ContentBlock, ContentType


@dataclass
class DocumentMetadata:
    """Enhanced metadata for RAG systems."""
    # Basic info
    filename: str
    source_path: str
    total_pages: int
    
    # Document properties
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    
    # Structure
    sections: List[str] = field(default_factory=list)
    table_count: int = 0
    image_count: int = 0
    chart_count: int = 0
    
    # Content statistics
    word_count: int = 0
    char_count: int = 0
    avg_words_per_page: float = 0.0
    
    # Extracted entities (for search optimization)
    dates: List[str] = field(default_factory=list)
    numbers: List[str] = field(default_factory=list)
    emails: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)
    
    # Language and type hints
    detected_language: Optional[str] = None
    document_type: Optional[str] = None  # report, invoice, manual, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "source_path": self.source_path,
            "total_pages": self.total_pages,
            "title": self.title,
            "author": self.author,
            "subject": self.subject,
            "keywords": self.keywords,
            "creation_date": self.creation_date,
            "modification_date": self.modification_date,
            "sections": self.sections,
            "table_count": self.table_count,
            "image_count": self.image_count,
            "chart_count": self.chart_count,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "avg_words_per_page": self.avg_words_per_page,
            "dates": self.dates,
            "numbers": self.numbers,
            "emails": self.emails,
            "urls": self.urls,
            "detected_language": self.detected_language,
            "document_type": self.document_type,
        }
    
    def to_search_text(self) -> str:
        """Generate searchable text from metadata."""
        parts = []
        if self.title:
            parts.append(f"Title: {self.title}")
        if self.author:
            parts.append(f"Author: {self.author}")
        if self.subject:
            parts.append(f"Subject: {self.subject}")
        if self.keywords:
            parts.append(f"Keywords: {', '.join(self.keywords)}")
        if self.sections:
            parts.append(f"Sections: {', '.join(self.sections)}")
        return " | ".join(parts)


class MetadataExtractor:
    """
    Extracts rich metadata from documents for enhanced RAG search.
    
    Features:
    - Document structure analysis
    - Entity extraction (dates, numbers, emails, URLs)
    - Content statistics
    - Language detection
    - Document type classification
    """
    
    # Regex patterns for entity extraction
    PATTERNS = {
        "date": [
            r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",  # MM/DD/YYYY
            r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b",    # YYYY-MM-DD
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b",
        ],
        "email": [r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"],
        "url": [r"https?://[^\s<>\"{}|\\^`\[\]]+"],
        "number": [r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b"],  # Numbers with commas
        "phone": [r"\b(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"],
    }
    
    def __init__(self):
        self._compiled_patterns = {
            key: [re.compile(p, re.IGNORECASE) for p in patterns]
            for key, patterns in self.PATTERNS.items()
        }
    
    def extract(self, document: PDFDocument) -> DocumentMetadata:
        """Extract metadata from a parsed PDF document."""
        
        # Basic info
        metadata = DocumentMetadata(
            filename=document.filename,
            source_path=document.source_path,
            total_pages=document.total_pages,
            title=document.metadata.get("title"),
            author=document.metadata.get("author"),
            subject=document.metadata.get("subject"),
            creation_date=document.metadata.get("creation_date"),
        )
        
        # Collect all text
        all_text = []
        for block in document.blocks:
            all_text.append(block.content)
            
            # Count content types
            if block.content_type == ContentType.TABLE:
                metadata.table_count += 1
            elif block.content_type == ContentType.IMAGE:
                metadata.image_count += 1
            elif block.content_type == ContentType.CHART:
                metadata.chart_count += 1
            elif block.content_type == ContentType.HEADER:
                metadata.sections.append(block.content)
        
        full_text = " ".join(all_text)
        
        # Content statistics
        metadata.char_count = len(full_text)
        metadata.word_count = len(full_text.split())
        if document.total_pages > 0:
            metadata.avg_words_per_page = metadata.word_count / document.total_pages
        
        # Entity extraction
        metadata.dates = self._extract_entities(full_text, "date")[:20]
        metadata.emails = self._extract_entities(full_text, "email")[:10]
        metadata.urls = self._extract_entities(full_text, "url")[:10]
        metadata.numbers = self._extract_significant_numbers(full_text)[:20]
        
        # Extract keywords from title and headers
        metadata.keywords = self._extract_keywords(document)
        
        # Language detection
        metadata.detected_language = self._detect_language(full_text)
        
        # Document type classification
        metadata.document_type = self._classify_document(document, full_text)
        
        return metadata
    
    def _extract_entities(self, text: str, entity_type: str) -> List[str]:
        """Extract entities of a specific type from text."""
        entities = set()
        for pattern in self._compiled_patterns.get(entity_type, []):
            matches = pattern.findall(text)
            entities.update(matches)
        return list(entities)
    
    def _extract_significant_numbers(self, text: str) -> List[str]:
        """Extract significant numbers (likely to be important values)."""
        numbers = []
        for pattern in self._compiled_patterns.get("number", []):
            matches = pattern.findall(text)
            for num in matches:
                # Filter out common non-significant numbers
                cleaned = num.replace(",", "")
                try:
                    value = float(cleaned)
                    # Keep numbers that are likely significant
                    if value > 100 or "," in num:  # Large numbers or formatted
                        numbers.append(num)
                except ValueError:
                    pass
        return list(set(numbers))
    
    def _extract_keywords(self, document: PDFDocument) -> List[str]:
        """Extract keywords from document structure."""
        keywords = set()
        
        # From title
        if document.metadata.get("title"):
            words = document.metadata["title"].split()
            keywords.update(w.lower() for w in words if len(w) > 3)
        
        # From headers
        for block in document.blocks:
            if block.content_type == ContentType.HEADER:
                words = block.content.split()
                keywords.update(w.lower() for w in words if len(w) > 3)
        
        # Remove common words
        stopwords = {"the", "and", "for", "with", "from", "that", "this", "have", "been"}
        keywords = keywords - stopwords
        
        return list(keywords)[:30]
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection based on common words."""
        text_lower = text.lower()
        
        # Common words in different languages
        lang_indicators = {
            "en": ["the", "and", "is", "are", "was", "were", "have", "has"],
            "ja": ["の", "は", "が", "を", "に", "で", "と", "です"],
            "zh": ["的", "是", "在", "有", "和", "了", "不", "我"],
            "ko": ["의", "은", "는", "이", "가", "을", "를", "에"],
            "de": ["der", "die", "und", "ist", "von", "mit", "für"],
            "fr": ["le", "la", "les", "de", "et", "est", "pour"],
        }
        
        scores = {}
        for lang, words in lang_indicators.items():
            score = sum(1 for w in words if w in text_lower)
            scores[lang] = score
        
        if scores:
            return max(scores, key=scores.get)
        return "unknown"
    
    def _classify_document(self, document: PDFDocument, text: str) -> str:
        """Classify document type based on content patterns."""
        text_lower = text.lower()
        
        # Check for common document types
        type_indicators = {
            "invoice": ["invoice", "bill to", "amount due", "payment", "total"],
            "report": ["executive summary", "conclusion", "findings", "analysis"],
            "manual": ["instructions", "step", "how to", "guide", "procedure"],
            "contract": ["agreement", "parties", "terms", "conditions", "hereby"],
            "resume": ["experience", "education", "skills", "employment"],
            "spreadsheet": [],  # Check for high table count
        }
        
        # High table count suggests spreadsheet-like document
        if document.total_pages > 0:
            tables_per_page = document.metadata.get("table_count", 0) / document.total_pages
            if tables_per_page > 0.5:
                return "spreadsheet"
        
        scores = {}
        for doc_type, indicators in type_indicators.items():
            score = sum(1 for ind in indicators if ind in text_lower)
            scores[doc_type] = score
        
        if scores:
            best_type = max(scores, key=scores.get)
            if scores[best_type] >= 2:
                return best_type
        
        return "document"  # Generic fallback


class CitationGenerator:
    """Generates formatted citations for RAG responses."""
    
    @staticmethod
    def generate_inline_citation(
        source_file: str,
        page_numbers: List[int],
        section: Optional[str] = None,
    ) -> str:
        """Generate an inline citation."""
        pages = sorted(set(page_numbers))
        if len(pages) == 1:
            page_str = f"p. {pages[0]}"
        else:
            page_str = f"pp. {pages[0]}-{pages[-1]}"
        
        if section:
            return f"[{source_file}, {section}, {page_str}]"
        return f"[{source_file}, {page_str}]"
    
    @staticmethod
    def generate_bibliography_entry(
        metadata: DocumentMetadata,
        access_date: Optional[str] = None,
    ) -> str:
        """Generate a bibliography-style citation."""
        parts = []
        
        if metadata.author:
            parts.append(metadata.author)
        
        if metadata.title:
            parts.append(f'"{metadata.title}"')
        else:
            parts.append(f'"{metadata.filename}"')
        
        if metadata.creation_date:
            parts.append(f"({metadata.creation_date})")
        
        if access_date:
            parts.append(f"Accessed: {access_date}")
        
        return ". ".join(parts) + "."
    
    @staticmethod
    def generate_visual_citation(
        bbox: Dict[str, Any],
        page_number: int,
    ) -> Dict[str, Any]:
        """Generate citation data for visual highlighting."""
        return {
            "page": page_number,
            "highlight": {
                "x": bbox["x0"],
                "y": bbox["y0"],
                "width": bbox["x1"] - bbox["x0"],
                "height": bbox["y1"] - bbox["y0"],
            }
        }
