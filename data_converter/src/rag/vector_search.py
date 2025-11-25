"""
Vector search utilities for RAG systems.
Optimizes embedding and retrieval for better citation accuracy.
"""

import re
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    """Represents a search result with citation info."""
    chunk_id: str
    content: str
    score: float
    
    # Citation info
    source_file: str
    page_numbers: List[int]
    section: Optional[str] = None
    
    # Visual citation support
    bboxes: List[Dict[str, Any]] = field(default_factory=list)
    
    # Content type info
    has_table: bool = False
    has_image: bool = False
    content_types: List[str] = field(default_factory=list)
    
    def get_citation(self) -> str:
        """Generate citation string."""
        pages = sorted(set(self.page_numbers))
        if len(pages) == 1:
            page_str = f"p. {pages[0]}"
        elif len(pages) == 2:
            page_str = f"pp. {pages[0]}, {pages[1]}"
        else:
            page_str = f"pp. {pages[0]}-{pages[-1]}"
        
        if self.section:
            return f"[{self.source_file}, {self.section}, {page_str}]"
        return f"[{self.source_file}, {page_str}]"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "score": self.score,
            "source": self.source_file,
            "pages": self.page_numbers,
            "section": self.section,
            "citation": self.get_citation(),
            "bboxes": self.bboxes,
            "has_table": self.has_table,
            "has_image": self.has_image,
        }


class QueryProcessor:
    """
    Processes queries for optimal vector search.
    
    Features:
    - Query expansion
    - Filter extraction
    - Hybrid search preparation
    """
    
    def __init__(self):
        # Patterns for extracting filters from queries
        self.filter_patterns = {
            "page": r"(?:page|p\.?)\s*(\d+)",
            "section": r"(?:section|chapter)\s+[\"']?([^\"']+)[\"']?",
            "file": r"(?:file|document)\s+[\"']?([^\"']+)[\"']?",
            "table": r"\b(table|chart|figure|image)\b",
        }
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a query and extract search parameters.
        
        Returns:
            Dict with 'query', 'filters', 'keywords', 'semantic_query'
        """
        filters = {}
        cleaned_query = query
        
        # Extract page filter
        page_match = re.search(self.filter_patterns["page"], query, re.IGNORECASE)
        if page_match:
            filters["page"] = int(page_match.group(1))
            cleaned_query = re.sub(self.filter_patterns["page"], "", cleaned_query, flags=re.IGNORECASE)
        
        # Extract section filter
        section_match = re.search(self.filter_patterns["section"], query, re.IGNORECASE)
        if section_match:
            filters["section"] = section_match.group(1)
            cleaned_query = re.sub(self.filter_patterns["section"], "", cleaned_query, flags=re.IGNORECASE)
        
        # Extract file filter
        file_match = re.search(self.filter_patterns["file"], query, re.IGNORECASE)
        if file_match:
            filters["file"] = file_match.group(1)
            cleaned_query = re.sub(self.filter_patterns["file"], "", cleaned_query, flags=re.IGNORECASE)
        
        # Check for content type hints
        table_match = re.search(self.filter_patterns["table"], query, re.IGNORECASE)
        if table_match:
            filters["content_type"] = table_match.group(1).lower()
        
        # Extract keywords for hybrid search
        keywords = self._extract_keywords(cleaned_query)
        
        # Clean up query
        cleaned_query = re.sub(r"\s+", " ", cleaned_query).strip()
        
        return {
            "original_query": query,
            "semantic_query": cleaned_query,
            "filters": filters,
            "keywords": keywords,
        }
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from query."""
        # Remove common question words
        stopwords = {
            "what", "where", "when", "how", "why", "who", "which",
            "is", "are", "was", "were", "do", "does", "did",
            "the", "a", "an", "in", "on", "at", "to", "for",
            "and", "or", "but", "not", "with", "from", "by",
            "can", "could", "would", "should", "will", "shall",
            "this", "that", "these", "those", "it", "its",
        }
        
        words = re.findall(r"\b[a-zA-Z]{3,}\b", query.lower())
        keywords = [w for w in words if w not in stopwords]
        
        return keywords
    
    def expand_query(self, query: str) -> List[str]:
        """
        Expand query with variations for better recall.
        
        Returns list of query variations.
        """
        variations = [query]
        
        # Add question variations
        if not query.endswith("?"):
            variations.append(f"What is {query}?")
            variations.append(f"How does {query} work?")
        
        # Add definition variation
        variations.append(f"{query} definition")
        variations.append(f"{query} explanation")
        
        return variations


class ResultReranker:
    """
    Re-ranks search results for better relevance.
    
    Features:
    - Diversity boosting
    - Content type boosting
    - Citation deduplication
    """
    
    def __init__(
        self,
        diversity_weight: float = 0.1,
        table_boost: float = 1.2,
        image_boost: float = 1.1,
    ):
        self.diversity_weight = diversity_weight
        self.table_boost = table_boost
        self.image_boost = image_boost
    
    def rerank(
        self,
        results: List[SearchResult],
        query_info: Dict[str, Any],
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        Re-rank search results.
        
        Args:
            results: Initial search results
            query_info: Processed query info from QueryProcessor
            top_k: Number of results to return
        """
        if not results:
            return []
        
        # Apply filters
        filtered_results = self._apply_filters(results, query_info.get("filters", {}))
        
        # Boost scores based on content type
        for result in filtered_results:
            if query_info.get("filters", {}).get("content_type") == "table" and result.has_table:
                result.score *= self.table_boost
            if query_info.get("filters", {}).get("content_type") in ("image", "figure", "chart") and result.has_image:
                result.score *= self.image_boost
        
        # Sort by score
        filtered_results.sort(key=lambda x: x.score, reverse=True)
        
        # Apply diversity
        if self.diversity_weight > 0:
            filtered_results = self._diversify(filtered_results, top_k)
        
        return filtered_results[:top_k]
    
    def _apply_filters(
        self,
        results: List[SearchResult],
        filters: Dict[str, Any],
    ) -> List[SearchResult]:
        """Apply filters to results."""
        filtered = results
        
        if "page" in filters:
            filtered = [r for r in filtered if filters["page"] in r.page_numbers]
        
        if "section" in filters:
            section_lower = filters["section"].lower()
            filtered = [r for r in filtered if r.section and section_lower in r.section.lower()]
        
        if "file" in filters:
            file_lower = filters["file"].lower()
            filtered = [r for r in filtered if file_lower in r.source_file.lower()]
        
        if "content_type" in filters:
            ct = filters["content_type"]
            if ct == "table":
                filtered = [r for r in filtered if r.has_table]
            elif ct in ("image", "figure", "chart"):
                filtered = [r for r in filtered if r.has_image]
        
        return filtered
    
    def _diversify(
        self,
        results: List[SearchResult],
        top_k: int,
    ) -> List[SearchResult]:
        """Apply diversity to avoid too many results from same source/section."""
        if len(results) <= top_k:
            return results
        
        selected = []
        seen_sources = {}
        seen_sections = {}
        
        for result in results:
            source_count = seen_sources.get(result.source_file, 0)
            section_key = f"{result.source_file}:{result.section}"
            section_count = seen_sections.get(section_key, 0)
            
            # Apply diversity penalty
            diversity_penalty = (source_count * 0.1 + section_count * 0.2) * self.diversity_weight
            adjusted_score = result.score * (1 - diversity_penalty)
            
            # Create new result with adjusted score
            adjusted_result = SearchResult(
                chunk_id=result.chunk_id,
                content=result.content,
                score=adjusted_score,
                source_file=result.source_file,
                page_numbers=result.page_numbers,
                section=result.section,
                bboxes=result.bboxes,
                has_table=result.has_table,
                has_image=result.has_image,
                content_types=result.content_types,
            )
            selected.append(adjusted_result)
            
            seen_sources[result.source_file] = source_count + 1
            seen_sections[section_key] = section_count + 1
        
        # Re-sort by adjusted score
        selected.sort(key=lambda x: x.score, reverse=True)
        
        return selected


class InlineCitationFormatter:
    """
    Formats search results with inline citations for LLM responses.
    """
    
    @staticmethod
    def format_context(
        results: List[SearchResult],
        include_sources: bool = True,
    ) -> str:
        """Format results as context for LLM."""
        parts = []
        
        for i, result in enumerate(results, 1):
            citation = result.get_citation()
            
            if include_sources:
                parts.append(f"[{i}] {citation}")
                parts.append(result.content)
                parts.append("")
            else:
                parts.append(f"[{i}] {result.content}")
        
        return "\n".join(parts)
    
    @staticmethod
    def format_response_with_citations(
        response: str,
        results: List[SearchResult],
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Format LLM response with proper inline citations.
        
        Returns:
            Tuple of (formatted_response, citation_metadata)
        """
        citation_map = {
            str(i): result for i, result in enumerate(results, 1)
        }
        
        # Find all citation references in response [1], [2], etc.
        citation_pattern = r"\[(\d+)\]"
        
        # Build citation metadata
        citations_used = []
        for match in re.finditer(citation_pattern, response):
            ref_num = match.group(1)
            if ref_num in citation_map:
                result = citation_map[ref_num]
                citations_used.append({
                    "ref": int(ref_num),
                    "source": result.source_file,
                    "pages": result.page_numbers,
                    "section": result.section,
                    "bboxes": result.bboxes,
                    "full_citation": result.get_citation(),
                })
        
        # Optionally expand citations in response
        def expand_citation(match):
            ref_num = match.group(1)
            if ref_num in citation_map:
                return citation_map[ref_num].get_citation()
            return match.group(0)
        
        expanded_response = re.sub(citation_pattern, expand_citation, response)
        
        return expanded_response, citations_used
    
    @staticmethod
    def generate_source_list(results: List[SearchResult]) -> str:
        """Generate a formatted list of sources."""
        sources = {}
        for result in results:
            key = result.source_file
            if key not in sources:
                sources[key] = {
                    "file": result.source_file,
                    "pages": set(),
                    "sections": set(),
                }
            sources[key]["pages"].update(result.page_numbers)
            if result.section:
                sources[key]["sections"].add(result.section)
        
        lines = ["**Sources:**"]
        for source in sources.values():
            pages = sorted(source["pages"])
            page_str = ", ".join(str(p) for p in pages)
            sections = sorted(source["sections"])
            
            line = f"- {source['file']}, Pages: {page_str}"
            if sections:
                line += f", Sections: {', '.join(sections)}"
            lines.append(line)
        
        return "\n".join(lines)
