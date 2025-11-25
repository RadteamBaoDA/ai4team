"""
LibreOffice converter implementation
"""

import subprocess
import tempfile
from pathlib import Path
from .base_converter import BaseConverter
from config.settings import LIBREOFFICE_COMMANDS, CONVERSION_TIMEOUT


class LibreOfficeConverter(BaseConverter):
    """Converts documents using LibreOffice"""
    
    def __init__(self):
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
                cmd = [
                    self._command, 
                    f'-env:UserInstallation={user_installation_url}',
                    '--headless', 
                    '--convert-to', 'pdf', 
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
                    return True
            
            return False
            
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False
