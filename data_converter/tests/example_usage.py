#!/usr/bin/env python3
"""
Example script demonstrating the Document Converter usage
"""

from pathlib import Path
from main import DocumentConverter


def example_basic_usage():
    """Basic usage example"""
    print("Example 1: Basic Usage")
    print("-" * 50)
    
    # Create converter
    converter = DocumentConverter(
        input_dir="./sample_documents",
        output_dir="./output_pdfs"
    )
    
    # Convert all documents
    stats = converter.convert_all()
    
    print(f"\nTotal: {stats['total']}")
    print(f"Success: {stats['success']}")
    print(f"Failed: {stats['failed']}")
    print()


def example_find_documents():
    """Example of finding documents before conversion"""
    print("Example 2: Find Documents First")
    print("-" * 50)
    
    converter = DocumentConverter(
        input_dir="./sample_documents",
        output_dir="./output_pdfs"
    )
    
    # Find all documents
    documents = converter.find_all_documents()
    
    print(f"Found {len(documents)} documents:")
    for doc in documents:
        print(f"  - {doc.name} ({doc.suffix})")
    print()


def example_single_file():
    """Example of converting a single file"""
    print("Example 3: Convert Single File")
    print("-" * 50)
    
    converter = DocumentConverter(
        input_dir="./sample_documents",
        output_dir="./output_pdfs"
    )
    
    # Convert specific file
    input_file = Path("./sample_documents/report.docx")
    
    if input_file.exists():
        success, output_path = converter.convert_file(input_file)
        
        if success:
            print(f"✓ Converted successfully")
            print(f"  Output: {output_path}")
        else:
            print(f"✗ Conversion failed")
    else:
        print(f"File not found: {input_file}")
    print()


def example_custom_processing():
    """Example of custom processing with filtering"""
    print("Example 4: Custom Processing")
    print("-" * 50)
    
    converter = DocumentConverter(
        input_dir="./sample_documents",
        output_dir="./output_pdfs"
    )
    
    # Find all documents
    documents = converter.find_all_documents()
    
    # Filter only DOCX files
    docx_files = [doc for doc in documents if doc.suffix.lower() == '.docx']
    
    print(f"Converting only DOCX files ({len(docx_files)} found):")
    
    success_count = 0
    for doc in docx_files:
        success, output_path = converter.convert_file(doc)
        if success:
            success_count += 1
    
    print(f"\nConverted {success_count}/{len(docx_files)} DOCX files")
    print()


def create_sample_structure():
    """Create sample directory structure for testing"""
    print("Creating sample directory structure...")
    
    base_dir = Path("./sample_documents")
    
    # Create directories
    dirs = [
        base_dir,
        base_dir / "reports" / "2023",
        base_dir / "reports" / "2024",
        base_dir / "presentations",
        base_dir / "spreadsheets"
    ]
    
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Created sample structure at: {base_dir.resolve()}")
    print("\nDirectory structure:")
    print("sample_documents/")
    print("├── reports/")
    print("│   ├── 2023/")
    print("│   └── 2024/")
    print("├── presentations/")
    print("└── spreadsheets/")
    print("\nPlace your test documents in these folders")
    print()


def main():
    """Run all examples"""
    print("=" * 70)
    print("Document Converter - Usage Examples")
    print("=" * 70)
    print()
    
    # Create sample structure
    create_sample_structure()
    
    print("=" * 70)
    print("To run examples, add some documents to ./sample_documents/")
    print("then uncomment the example calls below")
    print("=" * 70)
    print()
    
    # Uncomment to run examples (after adding test files):
    
    # example_basic_usage()
    # example_find_documents()
    # example_single_file()
    # example_custom_processing()


if __name__ == "__main__":
    main()
