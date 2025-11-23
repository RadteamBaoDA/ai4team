"""
File scanning utilities
"""

import os
from pathlib import Path
from typing import List, Tuple
from config.settings import SUPPORTED_EXTENSIONS, CONVERTIBLE_EXTENSIONS, COPY_EXTENSIONS


# Mapping of extension to postfix used when generating PDF filenames
POSTFIX_MAP = {
    '.txt': '_t',
    '.md': '_t',
    '.doc': '_d',
    '.docx': '_d',
    '.xls': '_x',
    '.xlsx': '_x',
    '.ppt': '_p',
    '.pptx': '_p',
}


class FileScanner:
    """Handles file scanning operations"""
    
    def __init__(self, input_dir: Path):
        """
        Initialize file scanner
        
        Args:
            input_dir: Directory to scan
        """
        self.input_dir = input_dir
    
    def find_all_documents(self) -> List[Path]:
        """
        Recursively find all supported documents in input directory
        
        Returns:
            List of Path objects for all found documents
        """
        documents = []
        
        for root, dirs, files in os.walk(self.input_dir):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    documents.append(file_path)
        
        return documents
    
    def categorize_files(self) -> Tuple[List[Path], List[Path]]:
        """
        Categorize files into convertible and copy-only
        
        Returns:
            Tuple of (files_to_convert, files_to_copy)
        """
        files_to_convert = []
        files_to_copy = []
        
        for root, dirs, files in os.walk(self.input_dir):
            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix.lower()
                
                if ext in CONVERTIBLE_EXTENSIONS:
                    files_to_convert.append(file_path)
                elif ext in COPY_EXTENSIONS:
                    files_to_copy.append(file_path)
        
        return files_to_convert, files_to_copy
    
    def get_output_path(self, input_file: Path, input_dir: Path, output_dir: Path) -> Path:
        """
        Calculate output path maintaining folder structure
        
        Args:
            input_file: Input file path
            input_dir: Base input directory
            output_dir: Base output directory
            
        Returns:
            Output file path with .pdf extension
        """
        # Get relative path from input directory
        relative_path = input_file.relative_to(input_dir)
        
        # Change extension to .pdf and add postfix when needed
        output_relative = relative_path.with_suffix('.pdf')
        postfix = POSTFIX_MAP.get(input_file.suffix.lower())
        if postfix:
            new_name = f"{output_relative.stem}{postfix}{output_relative.suffix}"
            output_relative = output_relative.with_name(new_name)
        
        # Construct full output path
        output_path = output_dir / output_relative
        
        # Create parent directories if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        return output_path
