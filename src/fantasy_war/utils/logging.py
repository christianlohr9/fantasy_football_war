"""Logging configuration for Fantasy WAR system."""

import sys
from pathlib import Path
from loguru import logger

from fantasy_war.config.settings import settings


def setup_logging(
    level: str = None,
    log_file: Path = None,
    enable_file_logging: bool = True
):
    """Setup logging configuration for the Fantasy WAR system.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file, uses default if None
        enable_file_logging: Whether to enable file logging
    """
    # Remove default logger
    logger.remove()
    
    # Use settings if not provided
    level = level or settings.logging.level
    log_file = log_file or Path("logs/fantasy_war.log")
    
    # Console logging
    logger.add(
        sys.stdout,
        level=level,
        format=settings.logging.format,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # File logging
    if enable_file_logging:
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            str(log_file),
            level=level,
            format=settings.logging.format,
            rotation=settings.logging.rotation,
            retention=settings.logging.retention,
            compression="gz",
            backtrace=True,
            diagnose=True,
        )
    
    logger.info(f"Logging configured: level={level}, file_logging={enable_file_logging}")


def get_logger(name: str = None):
    """Get a logger instance for a specific module.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    if name:
        return logger.bind(name=name)
    return logger