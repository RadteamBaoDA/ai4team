#!/usr/bin/env python3
"""
Document Converter Application
Converts DOCX, XLSX, PPTX files to PDF while preserving formatting
Maintains folder structure in output directory

New features:
- Default input/output folders in current directory
- Microsoft Office 365 support as fallback
- Optimized code structure following Python best practices
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.document_converter import DocumentConverter



def main():
    """Main entry point"""
    print("=" * 70)
    print("Document to PDF Converter v2.4")
    print("Parallel Processing | Smart Retry | Hash Optimization")
    print("=" * 70)
    print()
    
    # Get input directory (defaults to ./input)
    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
    else:
        default_input = str(Path(__file__).parent / "input")
        input_prompt = f"Enter input directory path (default: {default_input}): "
        input_dir = input(input_prompt).strip()
        if not input_dir:
            input_dir = None  # Will use default
    
    # Get output directory (defaults to ./output)
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]
    else:
        default_output = str(Path(__file__).parent / "output")
        output_prompt = f"Enter output directory path (default: {default_output}): "
        output_dir = input(output_prompt).strip()
        if not output_dir:
            output_dir = None  # Will use default
    
    try:
        # Create converter with parallel processing enabled
        converter = DocumentConverter(input_dir, output_dir, enable_parallel=True)
        
        print("\nStarting conversion with parallel processing...\n")
        stats = converter.convert_all()
        
        # Print summary
        print("\n" + "=" * 70)
        print("PROCESSING SUMMARY")
        print("=" * 70)
        print(f"Total files found:     {stats['total']}")
        print(f"Files converted:       {stats.get('converted', stats.get('success', 0))}")
        print(f"Files copied:          {stats.get('copied', 0)}")
        print(f"Failed:                {stats['failed']}")
        
        if stats['failed_files']:
            print("\nFailed files:")
            for file in stats['failed_files']:
                print(f"  - {file}")
        
        print("\n" + "=" * 70)
        
        converted = stats.get('converted', stats.get('success', 0))
        copied = stats.get('copied', 0)
        
        if converted > 0 or copied > 0:
            print(f"\n✓ Processed files saved to: {converter.output_dir}")
        
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
