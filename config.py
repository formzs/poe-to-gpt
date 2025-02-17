import os
import sys
import toml
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from config.toml file"""
    try:
        # Get the directory containing this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, "config.toml")
        
        logger.info(f"Loading config from {config_path}")
        return toml.load(config_path)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        # Provide more context in the error
        if isinstance(e, FileNotFoundError):
            logger.error(f"Please ensure config.toml exists in {os.path.dirname(config_path)}")
        raise

# Initialize config at module level
config = load_config()

# Make it clear what should be imported
__all__ = ['config']