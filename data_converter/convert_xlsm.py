"""
XLSM to XLSX Converter

This script reads an input folder, processes all files:
- XLSM files: Convert to XLSX using Microsoft Excel
- Other files: Copy to output folder

Both operations preserve the folder structure.

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


def convert_xlsm_to_xlsx(input_file: Path, output_file: Path) -> bool:
    """
    Convert XLSM file to XLSX using Microsoft Excel via COM automation.
    
    Args:
        input_file: Path to the input XLSM file
        output_file: Path to the output XLSX file
        
    Returns:
        True if conversion successful, False otherwise
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
            return True
            
        finally:
            # Quit Excel
            excel.Quit()
            
    except ImportError:
        print("[ERROR] pywin32 is not installed. Install it with: pip install pywin32")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to convert {input_file}: {e}")
        return False


def copy_file(input_file: Path, output_file: Path) -> bool:
    """
    Copy a file to the output location.
    
    Args:
        input_file: Path to the input file
        output_file: Path to the output file
        
    Returns:
        True if copy successful, False otherwise
    """
    try:
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy the file
        shutil.copy2(input_file, output_file)
        
        print(f"[COPIED] {input_file} -> {output_file}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to copy {input_file}: {e}")
        return False


def process_folder(input_folder: Path, output_folder: Path) -> dict:
    """
    Process all files in the input folder.
    
    Args:
        input_folder: Path to the input folder
        output_folder: Path to the output folder
        
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
                
                if convert_xlsm_to_xlsx(input_file, output_file):
                    stats['converted'] += 1
                else:
                    stats['failed'] += 1
            else:
                # Copy other files
                output_file = output_folder / relative_path
                
                if copy_file(input_file, output_file):
                    stats['copied'] += 1
                else:
                    stats['failed'] += 1
    
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
    
    print("=" * 60)
    print("XLSM to XLSX Converter")
    print("=" * 60)
    print(f"Input folder:  {input_folder.resolve()}")
    print(f"Output folder: {output_folder.resolve()}")
    print("=" * 60)
    
    # Process the folder
    stats = process_folder(input_folder, output_folder)
    
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
