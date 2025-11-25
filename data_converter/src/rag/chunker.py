"""
Smart Chunker for RAG systems.
Splits documents into semantically meaningful chunks optimized for vector search.
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from .pdf_parser import ContentBlock, ContentType, PDFDocument


class ChunkStrategy(Enum):
    """Chunking strategies."""
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    HYBRID = "hybrid"  # Combines semantic boundaries with size limits


@dataclass
class Chunk:
    """Represents a chunk of content for vector embedding."""
    chunk_id: str
    content: str
    embedding_text: str  # Optimized text for embedding
    
    # Source information for citations
    source_file: str
    page_numbers: List[int]
    section_title: Optional[str] = None
    
    # Content metadata
    content_types: List[str] = field(default_factory=list)
    has_table: bool = False
    has_image: bool = False
    
    # Position info
    start_block_idx: int = 0
    end_block_idx: int = 0
    
    # For inline citations
    bboxes: List[Dict[str, Any]] = field(default_factory=list)
    
    # Chunk metadata
    token_count: int = 0
    char_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.chunk_id,
            "content": self.content,
            "embedding_text": self.embedding_text,
            "source": self.source_file,
            "pages": self.page_numbers,
            "section": self.section_title,
            "content_types": self.content_types,
            "has_table": self.has_table,
            "has_image": self.has_image,
            "bboxes": self.bboxes,
            "token_count": self.token_count,
            "char_count": self.char_count,
            "metadata": self.metadata
        }
    
    def get_citation(self) -> str:
        """Generate a citation string for this chunk."""
        pages_str = ", ".join(str(p) for p in sorted(set(self.page_numbers)))
        citation = f"{self.source_file}, Page {pages_str}"
        if self.section_title:
            citation = f"{self.source_file}, Section: {self.section_title}, Page {pages_str}"
        return citation


class SmartChunker:
    """
    Intelligent document chunker for RAG systems.
    
    Features:
    - Multiple chunking strategies
    - Semantic boundary detection
    - Overlap support for context preservation
    - Table and image handling
    - Token-aware chunking
    - Citation metadata preservation
    """
    
    def __init__(
        self,
        strategy: ChunkStrategy = ChunkStrategy.HYBRID,
        max_chunk_size: int = 1000,  # Characters
        min_chunk_size: int = 100,
        overlap: int = 100,
        respect_boundaries: bool = True,  # Respect semantic boundaries
        include_metadata_in_embedding: bool = True,
        tokenizer: Optional[Callable[[str], List[str]]] = None,
    ):
        self.strategy = strategy
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap
        self.respect_boundaries = respect_boundaries
        self.include_metadata_in_embedding = include_metadata_in_embedding
        self.tokenizer = tokenizer or self._simple_tokenizer
    
    def _simple_tokenizer(self, text: str) -> List[str]:
        """Simple whitespace tokenizer."""
        return text.split()
    
    def chunk_document(self, document: PDFDocument) -> List[Chunk]:
        """
        Chunk a parsed PDF document.
        
        Args:
            document: Parsed PDFDocument
            
        Returns:
            List of Chunk objects
        """
        if self.strategy == ChunkStrategy.FIXED_SIZE:
            return self._chunk_fixed_size(document)
        elif self.strategy == ChunkStrategy.SEMANTIC:
            return self._chunk_semantic(document)
        elif self.strategy == ChunkStrategy.SENTENCE:
            return self._chunk_by_sentence(document)
        elif self.strategy == ChunkStrategy.PARAGRAPH:
            return self._chunk_by_paragraph(document)
        else:  # HYBRID
            return self._chunk_hybrid(document)
    
    def _chunk_hybrid(self, document: PDFDocument) -> List[Chunk]:
        """
        Hybrid chunking: respects semantic boundaries while enforcing size limits.
        This is the recommended strategy for RAG systems.
        """
        chunks: List[Chunk] = []
        current_blocks: List[ContentBlock] = []
        current_size = 0
        current_section = None
        
        for block_idx, block in enumerate(document.blocks):
            block_text = block.get_embedding_text()
            block_size = len(block_text)
            
            # Check if this block starts a new section
            is_new_section = (
                block.content_type == ContentType.HEADER or
                (block.section_title and block.section_title != current_section)
            )
            
            # Finalize current chunk if:
            # 1. New section detected
            # 2. Size limit reached
            # 3. Special content (table/image) that should be its own chunk
            should_finalize = (
                (is_new_section and current_blocks and self.respect_boundaries) or
                (current_size + block_size > self.max_chunk_size and current_blocks) or
                (block.content_type in (ContentType.TABLE, ContentType.IMAGE, ContentType.FIGURE, ContentType.CHART))
            )
            
            if should_finalize:
                chunk = self._create_chunk(
                    document, current_blocks, 
                    block_idx - len(current_blocks), block_idx - 1
                )
                if chunk:
                    chunks.append(chunk)
                current_blocks = []
                current_size = 0
            
            # Handle special content (tables/images) as their own chunks
            if block.content_type in (ContentType.TABLE, ContentType.IMAGE, ContentType.FIGURE, ContentType.CHART):
                chunk = self._create_chunk(
                    document, [block], block_idx, block_idx
                )
                if chunk:
                    chunks.append(chunk)
            else:
                current_blocks.append(block)
                current_size += block_size
            
            current_section = block.section_title
        
        # Don't forget the last chunk
        if current_blocks:
            chunk = self._create_chunk(
                document, current_blocks,
                len(document.blocks) - len(current_blocks),
                len(document.blocks) - 1
            )
            if chunk:
                chunks.append(chunk)
        
        # Add overlap between chunks
        if self.overlap > 0:
            chunks = self._add_overlap(chunks)
        
        return chunks
    
    def _chunk_fixed_size(self, document: PDFDocument) -> List[Chunk]:
        """Simple fixed-size chunking."""
        # Concatenate all text
        full_text = "\n\n".join(
            block.get_embedding_text() for block in document.blocks
        )
        
        chunks = []
        start = 0
        chunk_idx = 0
        
        while start < len(full_text):
            end = min(start + self.max_chunk_size, len(full_text))
            
            # Try to break at word boundary
            if end < len(full_text):
                last_space = full_text.rfind(" ", start, end)
                if last_space > start:
                    end = last_space
            
            chunk_text = full_text[start:end].strip()
            if chunk_text:
                chunks.append(self._create_simple_chunk(
                    document, chunk_text, chunk_idx
                ))
                chunk_idx += 1
            
            start = end - self.overlap if self.overlap > 0 else end
        
        return chunks
    
    def _chunk_semantic(self, document: PDFDocument) -> List[Chunk]:
        """Chunk based on semantic boundaries (headers/sections)."""
        chunks = []
        current_section_blocks: List[ContentBlock] = []
        
        for block_idx, block in enumerate(document.blocks):
            if block.content_type == ContentType.HEADER and current_section_blocks:
                # Finalize previous section
                chunk = self._create_chunk(
                    document, current_section_blocks,
                    block_idx - len(current_section_blocks), block_idx - 1
                )
                if chunk:
                    chunks.append(chunk)
                current_section_blocks = []
            
            current_section_blocks.append(block)
        
        # Last section
        if current_section_blocks:
            chunk = self._create_chunk(
                document, current_section_blocks,
                len(document.blocks) - len(current_section_blocks),
                len(document.blocks) - 1
            )
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def _chunk_by_sentence(self, document: PDFDocument) -> List[Chunk]:
        """Chunk by sentences with size limits."""
        # Simple sentence splitting
        full_text = " ".join(
            block.content for block in document.blocks 
            if block.content_type == ContentType.TEXT
        )
        
        sentences = re.split(r'(?<=[.!?])\s+', full_text)
        
        chunks = []
        current_sentences = []
        current_size = 0
        
        for sentence in sentences:
            if current_size + len(sentence) > self.max_chunk_size and current_sentences:
                chunk_text = " ".join(current_sentences)
                chunks.append(self._create_simple_chunk(
                    document, chunk_text, len(chunks)
                ))
                current_sentences = []
                current_size = 0
            
            current_sentences.append(sentence)
            current_size += len(sentence)
        
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            chunks.append(self._create_simple_chunk(
                document, chunk_text, len(chunks)
            ))
        
        return chunks
    
    def _chunk_by_paragraph(self, document: PDFDocument) -> List[Chunk]:
        """Chunk by paragraphs (one paragraph per chunk, with merging for small ones)."""
        chunks = []
        current_blocks = []
        current_size = 0
        
        for block_idx, block in enumerate(document.blocks):
            block_text = block.content
            
            if current_size + len(block_text) > self.max_chunk_size and current_blocks:
                chunk = self._create_chunk(
                    document, current_blocks,
                    block_idx - len(current_blocks), block_idx - 1
                )
                if chunk:
                    chunks.append(chunk)
                current_blocks = []
                current_size = 0
            
            current_blocks.append(block)
            current_size += len(block_text)
        
        if current_blocks:
            chunk = self._create_chunk(
                document, current_blocks,
                len(document.blocks) - len(current_blocks),
                len(document.blocks) - 1
            )
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def _create_chunk(
        self,
        document: PDFDocument,
        blocks: List[ContentBlock],
        start_idx: int,
        end_idx: int
    ) -> Optional[Chunk]:
        """Create a chunk from a list of content blocks."""
        if not blocks:
            return None
        
        # Combine content
        content_parts = [block.content for block in blocks]
        content = "\n\n".join(content_parts)
        
        # Generate embedding text
        embedding_parts = [block.get_embedding_text() for block in blocks]
        if self.include_metadata_in_embedding:
            # Add source context
            embedding_parts.insert(0, f"Source: {document.filename}")
        embedding_text = "\n\n".join(embedding_parts)
        
        # Collect metadata
        page_numbers = list(set(b.page_number for b in blocks))
        content_types = list(set(b.content_type.value for b in blocks))
        section_title = blocks[0].section_title
        
        bboxes = [b.bbox.to_dict() for b in blocks if b.bbox]
        
        has_table = any(b.content_type == ContentType.TABLE for b in blocks)
        has_image = any(b.content_type in (ContentType.IMAGE, ContentType.FIGURE, ContentType.CHART) for b in blocks)
        
        # Generate chunk ID
        chunk_id = self._generate_chunk_id(document.source_path, start_idx, end_idx)
        
        # Count tokens
        tokens = self.tokenizer(embedding_text)
        
        return Chunk(
            chunk_id=chunk_id,
            content=content,
            embedding_text=embedding_text,
            source_file=document.filename,
            page_numbers=page_numbers,
            section_title=section_title,
            content_types=content_types,
            has_table=has_table,
            has_image=has_image,
            start_block_idx=start_idx,
            end_block_idx=end_idx,
            bboxes=bboxes,
            token_count=len(tokens),
            char_count=len(content),
            metadata=document.metadata
        )
    
    def _create_simple_chunk(
        self,
        document: PDFDocument,
        text: str,
        chunk_idx: int
    ) -> Chunk:
        """Create a simple chunk from text."""
        chunk_id = self._generate_chunk_id(document.source_path, chunk_idx, chunk_idx)
        tokens = self.tokenizer(text)
        
        return Chunk(
            chunk_id=chunk_id,
            content=text,
            embedding_text=f"Source: {document.filename}\n\n{text}" if self.include_metadata_in_embedding else text,
            source_file=document.filename,
            page_numbers=[1],  # Unknown without block info
            content_types=["text"],
            token_count=len(tokens),
            char_count=len(text),
            metadata=document.metadata
        )
    
    def _add_overlap(self, chunks: List[Chunk]) -> List[Chunk]:
        """Add overlap context from previous chunk."""
        if len(chunks) <= 1:
            return chunks
        
        for i in range(1, len(chunks)):
            prev_content = chunks[i-1].content
            overlap_text = prev_content[-self.overlap:] if len(prev_content) > self.overlap else prev_content
            
            # Add overlap context
            chunks[i].content = f"[...] {overlap_text}\n\n{chunks[i].content}"
            chunks[i].embedding_text = f"[Previous context:] {overlap_text}\n\n{chunks[i].embedding_text}"
        
        return chunks
    
    def _generate_chunk_id(self, source: str, start: int, end: int) -> str:
        """Generate a unique chunk ID."""
        content = f"{source}:{start}:{end}"
        return hashlib.md5(content.encode()).hexdigest()[:16]


def chunk_for_vector_db(
    pdf_path: str,
    strategy: ChunkStrategy = ChunkStrategy.HYBRID,
    max_chunk_size: int = 1000,
    overlap: int = 100,
) -> List[Dict[str, Any]]:
    """
    Convenience function to parse and chunk a PDF for vector database ingestion.
    
    Returns a list of dictionaries ready for embedding and storage.
    """
    from .pdf_parser import PDFParser
    
    parser = PDFParser(extract_images=True, extract_tables=True)
    document = parser.parse(pdf_path)
    
    chunker = SmartChunker(
        strategy=strategy,
        max_chunk_size=max_chunk_size,
        overlap=overlap
    )
    chunks = chunker.chunk_document(document)
    
    return [chunk.to_dict() for chunk in chunks]
