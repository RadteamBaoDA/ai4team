"""
XLSM to XLSX Converter

This script reads an input folder, processes all files:
- XLSM files: Convert to XLSX using Microsoft Excel
- Other files: Copy to output folder

Both operations preserve the folder structure.

Features:
- Logs successful and failed files to separate log files
- Copies failed files to an error folder

Usage:
    python convert_xlsm.py [input_folder] [output_folder]
    
Default:
    input_folder: ./input
    output_folder: ./output
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime


class ProcessingLogger:
    """Logger for tracking successful and failed file operations."""
    
    def __init__(self, log_folder: Path):
        """
        Initialize the logger.
        
        Args:
            log_folder: Path to the folder for log files
        """
        self.log_folder = log_folder
        self.log_folder.mkdir(parents=True, exist_ok=True)
        
        # Create timestamp for log file names
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.success_log = self.log_folder / f"success_{timestamp}.log"
        self.error_log = self.log_folder / f"error_{timestamp}.log"
        
        self.success_files = []
        self.error_files = []
    
    def log_success(self, input_file: Path, output_file: Path, operation: str):
        """Log a successful file operation."""
        # Use absolute paths for clarity
        entry = f"{operation}|{input_file.resolve()}|{output_file.resolve()}"
        self.success_files.append(entry)
    
    def log_error(self, input_file: Path, error_message: str, operation: str):
        """Log a failed file operation with full path and reason."""
        # Use absolute path and include detailed error reason
        full_path = str(input_file.resolve())
        entry = f"{operation}|{full_path}|REASON: {error_message}"
        self.error_files.append((input_file, entry, error_message))
    
    def save_logs(self):
        """Save logs to files."""
        # Save success log
        if self.success_files:
            with open(self.success_log, 'w', encoding='utf-8') as f:
                f.write(f"# Success Log - {datetime.now().isoformat()}\n")
                f.write(f"# Format: operation|full_input_path|full_output_path\n")
                f.write("=" * 80 + "\n")
                for entry in self.success_files:
                    f.write(entry + "\n")
            print(f"[LOG] Success log saved: {self.success_log}")
        
        # Save error log
        if self.error_files:
            with open(self.error_log, 'w', encoding='utf-8') as f:
                f.write(f"# Error Log - {datetime.now().isoformat()}\n")
                f.write(f"# Format: operation|full_input_path|REASON: error_message\n")
                f.write(f"# Each entry contains the full absolute path and detailed failure reason\n")
                f.write("=" * 80 + "\n")
                for _, entry, _ in self.error_files:
                    f.write(entry + "\n")
            print(f"[LOG] Error log saved: {self.error_log}")
    
    def get_error_files(self) -> list:
        """Get list of files that had errors with their error messages."""
        return [(file_path, error_msg) for file_path, _, error_msg in self.error_files]


def copy_error_files(error_files: list, input_folder: Path, error_folder: Path):
    """
    Copy files that had errors to the error folder and create error reason files.
    
    Args:
        error_files: List of tuples (file_path, error_message) that had errors
        input_folder: Path to the input folder (for relative path calculation)
        error_folder: Path to the error folder
    """
    if not error_files:
        return
    
    error_folder.mkdir(parents=True, exist_ok=True)
    
    for input_file, error_msg in error_files:
        try:
            # Calculate relative path to preserve folder structure
            relative_path = input_file.relative_to(input_folder)
            error_file = error_folder / relative_path
            
            # Ensure output directory exists
            error_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the file
            shutil.copy2(input_file, error_file)
            print(f"[ERROR COPY] {input_file.resolve()} -> {error_file.resolve()}")
            
            # Create a .error.txt file with the failure reason
            error_reason_file = error_file.with_suffix(error_file.suffix + '.error.txt')
            with open(error_reason_file, 'w', encoding='utf-8') as f:
                f.write(f"Error Report\n")
                f.write("=" * 60 + "\n")
                f.write(f"Original File: {input_file.resolve()}\n")
                f.write(f"Error File Copy: {error_file.resolve()}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write("=" * 60 + "\n")
                f.write(f"FAILURE REASON:\n")
                f.write(f"{error_msg}\n")
            print(f"[ERROR REASON] Created: {error_reason_file}")
            
        except Exception as e:
            print(f"[ERROR] Failed to copy error file {input_file.resolve()}: {e}")


def convert_xlsm_to_xlsx(input_file: Path, output_file: Path) -> tuple[bool, str]:
    """
    Convert XLSM file to XLSX using Microsoft Excel via COM automation.
    
    Args:
        input_file: Path to the input XLSM file
        output_file: Path to the output XLSX file
        
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    try:
        import win32com.client as win32
        
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert paths to absolute paths
        input_path = str(input_file.resolve())
        output_path = str(output_file.resolve())
        
        # Open Excel application
        excel = win32.gencache.EnsureDispatch('Excel.Application')
        excel.Visible = False
        excel.DisplayAlerts = False
        
        try:
            # Open the workbook
            workbook = excel.Workbooks.Open(input_path)
            
            # Save as XLSX (FileFormat=51 is xlsx)
            workbook.SaveAs(output_path, FileFormat=51)
            
            # Close the workbook
            workbook.Close(SaveChanges=False)
            
            print(f"[CONVERTED] {input_file} -> {output_file}")
            return True, ""
            
        finally:
            # Quit Excel
            excel.Quit()
            
    except ImportError:
        error_msg = "pywin32 is not installed. Install it with: pip install pywin32"
        print(f"[ERROR] {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Failed to convert {input_file}: {error_msg}")
        return False, error_msg


def copy_file(input_file: Path, output_file: Path) -> tuple[bool, str]:
    """
    Copy a file to the output location.
    
    Args:
        input_file: Path to the input file
        output_file: Path to the output file
        
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    try:
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy the file
        shutil.copy2(input_file, output_file)
        
        print(f"[COPIED] {input_file} -> {output_file}")
        return True, ""
        
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Failed to copy {input_file}: {error_msg}")
        return False, error_msg


def process_folder(input_folder: Path, output_folder: Path, logger: ProcessingLogger) -> dict:
    """
    Process all files in the input folder.
    
    Args:
        input_folder: Path to the input folder
        output_folder: Path to the output folder
        logger: ProcessingLogger instance for tracking success/error
        
    Returns:
        Dictionary with statistics
    """
    stats = {
        'converted': 0,
        'copied': 0,
        'failed': 0,
        'total': 0
    }
    
    if not input_folder.exists():
        print(f"[ERROR] Input folder does not exist: {input_folder}")
        return stats
    
    # Create output folder if it doesn't exist
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Walk through all files in input folder
    for root, dirs, files in os.walk(input_folder):
        root_path = Path(root)
        
        for file_name in files:
            input_file = root_path / file_name
            
            # Calculate relative path to preserve folder structure
            relative_path = input_file.relative_to(input_folder)
            
            stats['total'] += 1
            
            # Check if file is XLSM
            if file_name.lower().endswith('.xlsm'):
                # Change extension to .xlsx for output
                output_file_name = Path(file_name).stem + '.xlsx'
                output_relative = relative_path.parent / output_file_name
                output_file = output_folder / output_relative
                
                success, error_msg = convert_xlsm_to_xlsx(input_file, output_file)
                if success:
                    stats['converted'] += 1
                    logger.log_success(input_file, output_file, "CONVERT")
                else:
                    stats['failed'] += 1
                    logger.log_error(input_file, error_msg, "CONVERT")
            else:
                # Copy other files
                output_file = output_folder / relative_path
                
                success, error_msg = copy_file(input_file, output_file)
                if success:
                    stats['copied'] += 1
                    logger.log_success(input_file, output_file, "COPY")
                else:
                    stats['failed'] += 1
                    logger.log_error(input_file, error_msg, "COPY")
    
    return stats


def main():
    """Main entry point."""
    # Parse command line arguments
    if len(sys.argv) >= 3:
        input_folder = Path(sys.argv[1])
        output_folder = Path(sys.argv[2])
    elif len(sys.argv) == 2:
        input_folder = Path(sys.argv[1])
        output_folder = Path('./output')
    else:
        input_folder = Path('./input')
        output_folder = Path('./output')
    
    # Setup folders
    log_folder = Path('./logs')
    error_folder = Path('./errors')
    
    print("=" * 60)
    print("XLSM to XLSX Converter")
    print("=" * 60)
    print(f"Input folder:  {input_folder.resolve()}")
    print(f"Output folder: {output_folder.resolve()}")
    print(f"Log folder:    {log_folder.resolve()}")
    print(f"Error folder:  {error_folder.resolve()}")
    print("=" * 60)
    
    # Initialize logger
    logger = ProcessingLogger(log_folder)
    
    # Process the folder
    stats = process_folder(input_folder, output_folder, logger)
    
    # Save logs
    logger.save_logs()
    
    # Copy error files to error folder
    error_files = logger.get_error_files()
    if error_files:
        print("=" * 60)
        print(f"Copying {len(error_files)} error file(s) to error folder...")
        copy_error_files(error_files, input_folder, error_folder)
    
    # Print summary
    print("=" * 60)
    print("Summary:")
    print(f"  Total files:     {stats['total']}")
    print(f"  XLSM converted:  {stats['converted']}")
    print(f"  Files copied:    {stats['copied']}")
    print(f"  Failed:          {stats['failed']}")
    print("=" * 60)
    
    return 0 if stats['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
