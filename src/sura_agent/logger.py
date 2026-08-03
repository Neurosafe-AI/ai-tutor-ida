import logging
import os
import sys
import re
from .telemetry import detector

CLS = "\033[0m"      
BLUE = "\033[94m"     
YELLOW = "\033[93m"   
GREEN = "\033[92m"    
MAGENTA = "\033[95m"  
BOLD_RED = "\033[1;31m"

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        return super().format(record)

class StripColorFormatter(logging.Formatter):
    def format(self, record):
        msg = super().format(record)
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', msg)

def get_sura_logger():
    logger = logging.getLogger("sura_agent")
    if logger.hasHandlers():
        return logger
    
    logger.setLevel(logging.INFO)
    logger.propagate = False
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter("%(message)s"))
    logger.addHandler(console_handler)
    
    base_root = os.path.abspath(os.path.expanduser(detector.get_server_root()))
    if os.path.exists(base_root):
        log_file = os.path.join(base_root, "sura_agent_telemetry.log")
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_formatter = StripColorFormatter("[%(asctime)s] %(levelname)s: %(message)s")
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception:
            pass

    return logger

logger = get_sura_logger()
