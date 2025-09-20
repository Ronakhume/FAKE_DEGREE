#!/usr/bin/env python3
"""
Simple logging example for GitHub Codespaces
Demonstrates logging to console and file
"""

import logging
import os
from datetime import datetime

def setup_logger():
    """Setup logging configuration for both console and file output"""
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('codespace_logger')
    logger.setLevel(logging.DEBUG)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    log_filename = f"logs/codespace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

def main():
    """Main function to demonstrate logging in codespace"""
    logger = setup_logger()
    
    logger.info("Starting logging demonstration in GitHub Codespace")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Environment: {os.environ.get('CODESPACE_NAME', 'Local')}")
    
    # Log different levels
    logger.debug("This is a debug message (only in file)")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Log some codespace-specific information
    if 'CODESPACE_NAME' in os.environ:
        logger.info(f"Running in GitHub Codespace: {os.environ['CODESPACE_NAME']}")
        logger.info(f"Codespace URL: {os.environ.get('GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN', 'N/A')}")
    else:
        logger.info("Running in local environment")
    
    logger.info("Logging demonstration completed")
    logger.info("Check the 'logs' directory for detailed log files")

if __name__ == "__main__":
    main()