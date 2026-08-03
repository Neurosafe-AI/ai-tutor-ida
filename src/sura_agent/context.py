"""
SURA Agent - Context Builder

This module manages reading, parsing, and caching workspace files. It allows the Agent
to perform static analysis on Jupyter notebooks (stripping out raw JSON and leaving
clean code cells) and standard Python files, injecting them into the LLM context window.
"""
import os
import json
from .telemetry import detector
from .logger import logger, YELLOW, CLS

class ContextBuilder:
    def __init__(self):
        self.file_cache = {}

    def read_and_cache_file(self, file_path: str) -> str:
        if not file_path:
            return "Error: Empty file path provided."
            
        file_path = file_path.strip("<>()[]\"' ")
        if file_path in self.file_cache:
            logger.info(f"{YELLOW}        [Cache Hit] Serving memory vector for: {file_path}{CLS}")
            return self.file_cache[file_path]
            
        base_root = os.path.abspath(os.path.expanduser(detector.get_server_root()))
        clean_path = os.path.normpath(os.path.join(base_root, file_path))
        
        if os.path.basename(clean_path).startswith('.') or os.path.basename(clean_path).startswith('.~'):
            return f"Error: Access to system file '{file_path}' is restricted."
        if not os.path.exists(clean_path):
            return f"Error: File '{file_path}' not found at path '{clean_path}'."
            
        try:
            with open(clean_path, "r", encoding="utf-8") as f:
                raw_content = f.read()
                
            if clean_path.endswith('.ipynb'):
                try:
                    notebook_json = json.loads(raw_content)
                    cleaned_cells = []
                    for index, cell in enumerate(notebook_json.get('cells', [])):
                        cell_type = cell.get('cell_type', 'code')
                        source_lines = "".join(cell.get('source', []))
                        cleaned_cells.append(f"--- [CELL #{index + 1} | TYPE: {cell_type.upper()}] ---\n{source_lines}")
                    processed_content = "\n\n".join(cleaned_cells)
                except Exception:
                    processed_content = raw_content
            else:
                processed_content = raw_content
                
            self.file_cache[file_path] = processed_content
            logger.info(f"{YELLOW}        [Cache Populated] Indexed repository asset: {file_path}{CLS}")
            return processed_content
            
        except Exception as e:
            return f"Error parsing workspace file: {str(e)}"

    def list_workspace_files(self) -> list:
        file_list = []
        base_root = os.path.abspath(os.path.expanduser(detector.get_server_root()))
        if not os.path.exists(base_root):
            return file_list

        for root, dirs, files in os.walk(base_root):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if not (file.startswith('.') or file.startswith('.~')) and file.endswith(('.py', '.ipynb')):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, base_root)
                    file_list.append(rel_path)
        return file_list
