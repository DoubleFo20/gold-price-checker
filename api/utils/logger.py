import logging
import os
import sys

def setup_logger(name=__name__):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console Handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # Avoid propagating to root logger
        logger.propagate = False
        
    return logger

# Global instance for quick use
log = setup_logger("gold_price_checker")
