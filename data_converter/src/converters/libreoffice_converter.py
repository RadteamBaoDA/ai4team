"""
LibreOffice converter implementation
"""

import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from .base_converter import BaseConverter
from ..utils import setup_logger
from config.settings import (
    LIBREOFFICE_COMMANDS,
    CONVERSION_TIMEOUT,
    RAG_OPTIMIZATION_ENABLED,
    PDF_CREATE_BOOKMARKS,
    PDF_CREATE_TAGGED,
    PDF_EMBED_FONTS,
    PDF_USE_ISO19005,
    CITATION_INCLUDE_FILENAME,
    CITATION_INCLUDE_PAGE,
    CITATION_INCLUDE_DATE,
    CITATION_DATE_FORMAT,
)


class LibreOfficeConverter(BaseConverter):
    """Converts documents using LibreOffice"""
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        self._command = None
        self._check_availability()
    
    def _check_availability(self):
        """Check which LibreOffice command is available"""
        for cmd in LIBREOFFICE_COMMANDS:
            try:
                result = subprocess.run(
                    [cmd, '--version'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self._command = cmd
                    return
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
    
    def is_available(self) -> bool:
        """Check if LibreOffice is available"""
        return self._command is not None
    
    def convert(self, input_file: Path, output_file: Path) -> bool:
        """
        Convert document using LibreOffice
        
        Args:
            input_file: Source file
            output_file: Destination PDF file
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            output_dir = output_file.parent
            
            # Create a temporary directory for the user profile to avoid lock issues in parallel mode
            with tempfile.TemporaryDirectory() as temp_profile_dir:
                # Format path for LibreOffice URL (forward slashes)
                user_installation_url = f"file:///{str(Path(temp_profile_dir).as_posix())}"
                
                # Convert to PDF using LibreOffice
                # Added -env:UserInstallation to support parallel execution
                convert_to = self._build_pdf_filter_argument(input_file.suffix.lower())

                cmd = [
                    self._command, 
                    f'-env:UserInstallation={user_installation_url}',
                    '--headless', 
                    '--convert-to', convert_to,
                    '--outdir', str(output_dir), 
                    str(input_file)
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=CONVERSION_TIMEOUT
                )
                
                if result.returncode == 0:
                    # LibreOffice creates file with same name but .pdf extension
                    generated_pdf = output_dir / (input_file.stem + '.pdf')
                    if generated_pdf.exists() and generated_pdf != output_file:
                        generated_pdf.rename(output_file)
                    if output_file.exists():
                        self._apply_pdf_metadata(output_file, input_file)
                    return True
            
            return False
            
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    def _build_pdf_filter_argument(self, suffix: str) -> str:
        """Return the --convert-to argument with RAG-aware filter options."""
        if not RAG_OPTIMIZATION_ENABLED:
            return 'pdf'

        filter_name = self._resolve_filter_name(suffix)
        options = []

        if PDF_USE_ISO19005:
            options.append('SelectPdfVersion=1')  # PDF/A-1
        if PDF_CREATE_TAGGED:
            options.append('UseTaggedPDF=true')
        if PDF_CREATE_BOOKMARKS:
            options.append('ExportBookmarks=true')
        if PDF_EMBED_FONTS:
            options.append('EmbedStandardFonts=true')

        if not options:
            return f'pdf:{filter_name}'

        return f"pdf:{filter_name}:{';'.join(options)}"

    @staticmethod
    def _resolve_filter_name(suffix: str) -> str:
        if suffix in {'.xlsx', '.xls', '.ods', '.csv'}:
            return 'calc_pdf_Export'
        if suffix in {'.pptx', '.ppt', '.odp'}:
            return 'impress_pdf_Export'
        return 'writer_pdf_Export'

    def _apply_pdf_metadata(self, pdf_path: Path, input_file: Path) -> None:
        """Inject PDF metadata to align with MS Office exports."""
        if not RAG_OPTIMIZATION_ENABLED:
            return
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError:
            self.logger.debug("pypdf not installed; skipping metadata injection for %s", input_file.name)
            return

        try:
            reader = PdfReader(str(pdf_path))
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)

            page_count = len(reader.pages)
            metadata_parts = []
            keywords = [input_file.stem, 'LibreOffice', 'RAG']

            if CITATION_INCLUDE_FILENAME:
                metadata_parts.append(f"Source: {input_file.name}")
                keywords.append(input_file.name)
            if CITATION_INCLUDE_PAGE and page_count:
                metadata_parts.append(f"Pages: {page_count}")
                keywords.append(f"pages:{page_count}")
            if CITATION_INCLUDE_DATE:
                metadata_parts.append(f"Converted: {datetime.now().strftime(CITATION_DATE_FORMAT)}")

            title = input_file.stem
            metadata = {
                '/Title': title,
                '/Author': 'AI4Team Converter',
                '/Subject': 'RAG Export',
                '/Creator': 'LibreOffice',
                '/Producer': 'LibreOffice',
                '/Keywords': ', '.join(dict.fromkeys(keywords)),
            }
            if metadata_parts:
                metadata['/Comments'] = ' | '.join(metadata_parts)

            # Merge existing metadata to avoid losing info
            existing_metadata = dict(reader.metadata or {})
            existing_metadata.update(metadata)
            writer.add_metadata(existing_metadata)

            temp_path = pdf_path.parent / (pdf_path.name + '.tmp')
            with open(temp_path, 'wb') as pdf_file:
                writer.write(pdf_file)
            temp_path.replace(pdf_path)
        except Exception as metadata_error:
            self.logger.debug("Failed to inject metadata for %s: %s", input_file.name, metadata_error)
