"""
Centralized logging configuration for Friday AI Assistant.
"""

import logging
import sys
from pathlib import Path


def setup_logging(level=logging.INFO, log_file='data/logs/friday.log'):
    """Setup logging configuration for the entire application."""
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_file).parent
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=level,
        format='[%(asctime)s] %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, mode='a', encoding='utf-8')
        ],
        force=True  # This ensures it overrides any existing config
    )
    
    # Set specific loggers to warning to reduce noise
    logging.getLogger('chromadb').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    return logging.getLogger('Friday')