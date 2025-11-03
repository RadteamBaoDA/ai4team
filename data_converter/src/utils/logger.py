"""
Logging utility for Document Converter
"""

import logging
from datetime import datetime
from pathlib import Path
from config.settings import LOG_FORMAT, LOG_DIR


def setup_logger(name: str = __name__) -> logging.Logger:
    """
    Setup and return a configured logger
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    # Create log file with timestamp
    log_file = LOG_DIR / f'conversion_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    # Console handler with UTF-8 encoding
    import sys
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    # Set stream encoding to UTF-8 if possible
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
