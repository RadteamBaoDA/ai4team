"""
RAG (Retrieval Augmented Generation) utilities for PDF parsing and chunking.
Optimized for vector database ingestion and citation retrieval.
"""

from .pdf_parser import PDFParser, PDFDocument, ContentBlock, ContentType, BoundingBox
from .chunker import SmartChunker, Chunk, ChunkStrategy, chunk_for_vector_db
from .metadata_extractor import MetadataExtractor, DocumentMetadata, CitationGenerator
from .vector_search import (
    QueryProcessor, 
    ResultReranker, 
    SearchResult, 
    InlineCitationFormatter
)

__all__ = [
    # PDF Parser
    'PDFParser', 
    'PDFDocument', 
    'ContentBlock', 
    'ContentType',
    'BoundingBox',
    
    # Chunker
    'SmartChunker', 
    'Chunk',
    'ChunkStrategy',
    'chunk_for_vector_db',
    
    # Metadata
    'MetadataExtractor',
    'DocumentMetadata',
    'CitationGenerator',
    
    # Vector Search
    'QueryProcessor',
    'ResultReranker',
    'SearchResult',
    'InlineCitationFormatter',
]
