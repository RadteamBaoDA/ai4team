"""
Base converter interface
"""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseConverter(ABC):
    """Abstract base class for document converters"""
    
    @abstractmethod
    def convert(self, input_file: Path, output_file: Path) -> bool:
        """
        Convert a document to PDF
        
        Args:
            input_file: Source file
            output_file: Destination PDF file
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this converter is available on the system
        
        Returns:
            True if converter can be used, False otherwise
        """
        pass
