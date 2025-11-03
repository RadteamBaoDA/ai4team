"""
Main Document Converter class with parallel processing and retry support
v2.5: Adaptive workers, priority queue, progress bars, batch optimization, persistent cache
"""

import os
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from .converters import ConverterFactory
from .utils import setup_logger, FileScanner
from .utils.file_hash import should_skip_conversion, should_skip_copy
from config.settings import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR

# Optional progress bar support
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    # Fallback: simple progress tracker
    class tqdm:
        def __init__(self, iterable=None, total=None, desc=None, **kwargs):
            self.iterable = iterable
            self.total = total
            self.desc = desc
            self.n = 0
        
        def __iter__(self):
            return iter(self.iterable) if self.iterable else iter([])
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
        
        def update(self, n=1):
            self.n += n
        
        def set_description(self, desc):
            self.desc = desc


class DocumentConverter:
    """Handles conversion of Office documents to PDF format with parallel processing
    
    v2.5 Features:
    - Adaptive worker count based on file sizes
    - Priority queue for large files
    - Visual progress bars
    - Batch optimization for small files
    - Persistent hash cache
    """
    
    def __init__(self, input_dir: Optional[str] = None, output_dir: Optional[str] = None, 
                 max_workers: Optional[int] = None, enable_parallel: bool = True,
                 enable_progress_bar: bool = True, adaptive_workers: bool = True,
                 priority_large_files: bool = True, batch_small_files: bool = True):
        """
        Initialize the converter
        
        Args:
            input_dir: Source directory containing documents (default: ./input)
            output_dir: Destination directory for converted PDFs (default: ./output)
            max_workers: Maximum number of parallel workers (default: CPU cores / 2)
            enable_parallel: Enable parallel processing (default: True)
            enable_progress_bar: Show progress bar during conversion (default: True)
            adaptive_workers: Adjust worker count based on file sizes (default: True)
            priority_large_files: Process large files first (default: True)
            batch_small_files: Group small files for efficiency (default: True)
        """
        # Use default directories if not provided
        if input_dir is None:
            self.input_dir = DEFAULT_INPUT_DIR
        else:
            self.input_dir = Path(input_dir).resolve()
        
        if output_dir is None:
            self.output_dir = DEFAULT_OUTPUT_DIR
        else:
            self.output_dir = Path(output_dir).resolve()
        
        # Create input directory if it doesn't exist
        self.input_dir.mkdir(parents=True, exist_ok=True)
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Parallel processing configuration
        self.enable_parallel = enable_parallel
        if max_workers is None:
            # Default: CPU cores / 2, minimum 1
            cpu_count = os.cpu_count() or 2
            self.max_workers = max(1, cpu_count // 2)
        else:
            self.max_workers = max(1, max_workers)
        
        # v2.5 features
        self.enable_progress_bar = enable_progress_bar and TQDM_AVAILABLE
        self.adaptive_workers = adaptive_workers
        self.priority_large_files = priority_large_files
        self.batch_small_files = batch_small_files
        
        # File size thresholds (in bytes)
        self.SMALL_FILE_THRESHOLD = 100 * 1024  # 100KB
        self.LARGE_FILE_THRESHOLD = 10 * 1024 * 1024  # 10MB
        
        # Thread-safe lock for statistics
        self.stats_lock = Lock()
        
        # Initialize components
        self.logger = setup_logger(__name__)
        self.scanner = FileScanner(self.input_dir)
        self.converter_factory = ConverterFactory()
        
        # Log initialization
        self.logger.info(f"Input directory: {self.input_dir}")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"Parallel processing: {'Enabled' if self.enable_parallel else 'Disabled'}")
        if self.enable_parallel:
            self.logger.info(f"Max workers: {self.max_workers}")
        
        # Log available converters
        available = self.converter_factory.get_available_converters_info()
        self.logger.info("Available converters:")
        for name, status in available.items():
            status_str = "[OK] Available" if status else "[--] Not available"
            self.logger.info(f"  {name}: {status_str}")
    
    def find_all_documents(self) -> List[Path]:
        """
        Recursively find all supported documents in input directory
        
        Returns:
            List of Path objects for all found documents
        """
        self.logger.info("Scanning for documents...")
        documents = self.scanner.find_all_documents()
        self.logger.info(f"Found {len(documents)} documents to convert")
        return documents
    
    def get_output_path(self, input_file: Path) -> Path:
        """
        Calculate output path maintaining folder structure
        
        Args:
            input_file: Input file path
            
        Returns:
            Output file path with .pdf extension
        """
        return self.scanner.get_output_path(input_file, self.input_dir, self.output_dir)
    
    def convert_file(self, input_file: Path, retry_count: int = 1) -> Tuple[bool, Path]:
        """
        Convert a single file to PDF with retry support
        
        Args:
            input_file: Source file to convert
            retry_count: Number of retries on failure (default: 1)
            
        Returns:
            Tuple of (success status, output file path)
        """
        output_file = self.get_output_path(input_file)
        
        # Check if we can skip conversion (output exists and is up-to-date)
        if should_skip_conversion(input_file, output_file):
            self.logger.info(f"[SKIP] Output already exists and is up-to-date: {output_file.name}")
            return True, output_file
        
        self.logger.info(f"Converting: {input_file.name} -> {output_file.name}")
        
        # Get converters for this file type
        converters = self.converter_factory.get_converters_for_file(input_file)
        
        if not converters:
            self.logger.error(f"No converters available for {input_file.name}")
            return False, output_file
        
        # Try with retry logic
        for attempt in range(retry_count + 1):
            if attempt > 0:
                self.logger.info(f"[RETRY {attempt}/{retry_count}] Retrying: {input_file.name}")
            
            # Try each converter in order
            for converter in converters:
                converter_name = converter.__class__.__name__
                self.logger.debug(f"Trying {converter_name}...")
                
                try:
                    if converter.convert(input_file, output_file):
                        retry_msg = f" (retry {attempt})" if attempt > 0 else ""
                        self.logger.info(f"[OK] Successfully converted: {input_file.name}{retry_msg} (using {converter_name})")
                        return True, output_file
                except Exception as e:
                    self.logger.debug(f"{converter_name} failed: {e}")
                    continue
        
        # All converters and retries failed
        self.logger.error(f"[FAIL] Failed to convert: {input_file.name} (all converters failed after {retry_count} retries)")
        return False, output_file
    
    def copy_file(self, input_file: Path, retry_count: int = 1) -> Tuple[bool, Path]:
        """
        Copy a file to output directory maintaining structure with retry support
        
        Args:
            input_file: Source file to copy
            retry_count: Number of retries on failure (default: 1)
            
        Returns:
            Tuple of (success status, output file path)
        """
        import shutil
        import time
        
        output_file = self.get_output_path(input_file)
        # Keep original extension for copied files
        output_file = output_file.with_suffix(input_file.suffix)
        
        # Check if we can skip copy (output exists and is identical)
        if should_skip_copy(input_file, output_file):
            self.logger.info(f"[SKIP] File already exists and is identical: {output_file.name}")
            return True, output_file
        
        self.logger.info(f"Copying: {input_file.name}")
        
        # Try with retry logic
        for attempt in range(retry_count + 1):
            if attempt > 0:
                self.logger.info(f"[RETRY {attempt}/{retry_count}] Retrying copy: {input_file.name}")
                time.sleep(0.1)  # Brief delay before retry
            
            try:
                shutil.copy2(input_file, output_file)
                retry_msg = f" (retry {attempt})" if attempt > 0 else ""
                self.logger.info(f"[OK] Successfully copied: {input_file.name}{retry_msg}")
                return True, output_file
            except Exception as e:
                if attempt < retry_count:
                    self.logger.warning(f"Copy failed, will retry: {input_file.name} - {e}")
                else:
                    self.logger.error(f"[FAIL] Failed to copy: {input_file.name} - {e}")
        
        return False, output_file
    
    def _process_file_wrapper(self, file_info: Tuple[Path, str]) -> Tuple[bool, str, Path]:
        """
        Wrapper for processing a file (convert or copy) - used for parallel execution
        
        Args:
            file_info: Tuple of (file_path, operation_type) where operation is 'convert' or 'copy'
            
        Returns:
            Tuple of (success, operation_type, file_path)
        """
        file_path, operation = file_info
        
        if operation == 'convert':
            success, _ = self.convert_file(file_path)
        else:  # operation == 'copy'
            success, _ = self.copy_file(file_path)
        
        return success, operation, file_path
    
    def _get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes"""
        try:
            return file_path.stat().st_size
        except Exception:
            return 0
    
    def _categorize_by_size(self, files: List[Path]) -> Dict[str, List[Path]]:
        """Categorize files by size for adaptive processing"""
        small_files = []
        medium_files = []
        large_files = []
        
        for file_path in files:
            size = self._get_file_size(file_path)
            if size < self.SMALL_FILE_THRESHOLD:
                small_files.append(file_path)
            elif size > self.LARGE_FILE_THRESHOLD:
                large_files.append(file_path)
            else:
                medium_files.append(file_path)
        
        return {
            'small': small_files,
            'medium': medium_files,
            'large': large_files
        }
    
    def _calculate_adaptive_workers(self, files_to_process: List[Path]) -> int:
        """Calculate optimal worker count based on file sizes"""
        if not self.adaptive_workers or not files_to_process:
            return self.max_workers
        
        # Categorize files
        categorized = self._categorize_by_size(files_to_process)
        
        total_files = len(files_to_process)
        large_count = len(categorized['large'])
        small_count = len(categorized['small'])
        
        # If mostly large files, use fewer workers (avoid resource contention)
        if large_count / total_files > 0.5:
            return max(1, self.max_workers // 2)
        
        # If mostly small files, use more workers (less resource intensive)
        elif small_count / total_files > 0.7:
            return min(self.max_workers * 2, (os.cpu_count() or 2))
        
        # Mixed or medium files, use default
        return self.max_workers
    
    def _sort_by_priority(self, files_to_convert: List[Path], files_to_copy: List[Path]) -> List[Tuple[Path, str]]:
        """Sort files by priority: large files first, then medium, then small"""
        if not self.priority_large_files:
            # No priority sorting, process as-is
            return [(f, 'convert') for f in files_to_convert] + [(f, 'copy') for f in files_to_copy]
        
        # Get file sizes and sort
        convert_with_sizes = [(f, 'convert', self._get_file_size(f)) for f in files_to_convert]
        copy_with_sizes = [(f, 'copy', self._get_file_size(f)) for f in files_to_copy]
        
        all_files = convert_with_sizes + copy_with_sizes
        
        # Sort by size descending (largest first)
        all_files.sort(key=lambda x: x[2], reverse=True)
        
        # Return without size info
        return [(f, op) for f, op, _ in all_files]
    
    def convert_all(self, enable_parallel: Optional[bool] = None) -> dict:
        """
        Convert all documents in input directory and copy non-convertible files
        Supports both parallel and sequential processing
        
        Args:
            enable_parallel: Override parallel processing setting (default: use instance setting)
        
        Returns:
            Dictionary with conversion statistics
        """
        # Categorize files
        files_to_convert, files_to_copy = self.scanner.categorize_files()
        
        total_files = len(files_to_convert) + len(files_to_copy)
        
        if total_files == 0:
            self.logger.warning("No files found to process")
            return {
                'total': 0, 
                'converted': 0, 
                'copied': 0,
                'skipped': 0,
                'failed': 0, 
                'failed_files': []
            }
        
        self.logger.info(f"Found {len(files_to_convert)} files to convert")
        self.logger.info(f"Found {len(files_to_copy)} files to copy")
        
        # Use instance setting if not overridden
        use_parallel = self.enable_parallel if enable_parallel is None else enable_parallel
        
        stats = {
            'total': total_files,
            'converted': 0,
            'copied': 0,
            'skipped': 0,
            'failed': 0,
            'failed_files': []
        }
        
        if use_parallel and total_files > 1:
            # Parallel processing with adaptive workers (v2.5)
            all_files = files_to_convert + files_to_copy
            adaptive_workers = self._calculate_adaptive_workers(all_files)
            worker_count = min(adaptive_workers, max(1, total_files))
            
            self.logger.info(f"Processing files in parallel with {worker_count} workers")
            if self.adaptive_workers and worker_count != self.max_workers:
                self.logger.info(f"Using adaptive worker count (base: {self.max_workers}, adjusted: {worker_count})")
            
            self._convert_all_parallel(files_to_convert, files_to_copy, stats, worker_count)
        else:
            # Sequential processing
            if not use_parallel:
                self.logger.info("Processing files sequentially (parallel disabled)")
            self._convert_all_sequential(files_to_convert, files_to_copy, stats)
        
        return stats

    def _convert_all_sequential(self, files_to_convert: List[Path], files_to_copy: List[Path], stats: dict):
        """Sequential processing of files"""
        # Convert files
        for doc in files_to_convert:
            success, output_path = self.convert_file(doc)
            
            if success:
                stats['converted'] += 1
            else:
                stats['failed'] += 1
                stats['failed_files'].append(str(doc))
        
        # Copy files
        for doc in files_to_copy:
            success, output_path = self.copy_file(doc)
            
            if success:
                stats['copied'] += 1
            else:
                stats['failed'] += 1
                stats['failed_files'].append(str(doc))
    
    def _convert_all_parallel(
        self,
        files_to_convert: List[Path],
        files_to_copy: List[Path],
        stats: dict,
        worker_count: int,
    ):
        """Parallel processing of files using ThreadPoolExecutor with v2.5 enhancements"""
        # Prepare work items with priority sorting
        work_items = self._sort_by_priority(files_to_convert, files_to_copy)
        
        # Process files in parallel
        if not work_items:
            return

        total_items = len(work_items)
        
        # Create progress bar
        progress_bar = None
        if self.enable_progress_bar:
            progress_bar = tqdm(
                total=total_items,
                desc="Processing files",
                unit="file",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
            )

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self._process_file_wrapper, item): item 
                for item in work_items
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                item = future_to_file[future]
                file_path, operation = item
                
                try:
                    success, op_type, processed_file = future.result()
                    
                    # Thread-safe statistics update
                    with self.stats_lock:
                        if success:
                            if op_type == 'convert':
                                stats['converted'] += 1
                            else:
                                stats['copied'] += 1
                        else:
                            stats['failed'] += 1
                            stats['failed_files'].append(str(processed_file))
                    
                    # Update progress bar
                    if progress_bar:
                        progress_bar.update(1)
                        if success:
                            progress_bar.set_description(f"✓ {file_path.name[:30]}")
                        else:
                            progress_bar.set_description(f"✗ {file_path.name[:30]}")
                            
                except Exception as e:
                    self.logger.error(f"Unexpected error processing {file_path.name}: {e}")
                    with self.stats_lock:
                        stats['failed'] += 1
                        stats['failed_files'].append(str(file_path))
                    
                    if progress_bar:
                        progress_bar.update(1)
        
        # Close progress bar
        if progress_bar:
            progress_bar.close()
