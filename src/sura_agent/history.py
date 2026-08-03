"""
SURA Agent - History Manager

This module manages the chat history persistence for the Jupyter AI Chat interface.
Because standard Jupyter AI personas often lose context between server restarts or
chat window reloads, this manager intercepts the history and saves it to a 
`.sura_history_*.json` file in the workspace.

It also includes a sweeper to clean up orphaned history files when the original
`.chat` file is deleted by the user.
"""
import os
import json
import time
import glob
import re
from .telemetry import detector
from .logger import logger, YELLOW, GREEN, BOLD_RED, CLS

class HistoryManager:
    def __init__(self, max_history_turns=12):
        self.max_history_turns = max_history_turns

    def get_chat_session_id(self, message) -> str:
        for attr in ['chat_path', 'file_path', 'session_id', 'thread_id']:
            val = getattr(message, attr, None)
            if val:
                return str(val)
        
        base_root = os.path.abspath(os.path.expanduser(detector.get_server_root()))
        if os.path.exists(base_root):
            try:
                chat_files = [f for f in os.listdir(base_root) if f.endswith('.chat') and not f.startswith('.')]
                if chat_files:
                    chat_files.sort(key=lambda x: os.path.getmtime(os.path.join(base_root, x)), reverse=True)
                    return chat_files[0]
            except Exception:
                pass
        return "default_chat_session"

    def get_history_filepath(self, session_id: str) -> str:
        base_root = os.path.abspath(os.path.expanduser(detector.get_server_root()))
        safe_session = re.sub(r'[^a-zA-Z0-9_\-]', '_', session_id)
        return os.path.join(base_root, f".sura_history_{safe_session}.json")

    def load_history(self, session_id: str) -> list:
        history_path = self.get_history_filepath(session_id)
        base_root = os.path.abspath(os.path.expanduser(detector.get_server_root()))
        chat_history = []

        if session_id.endswith(".chat"):
            chat_file_path = os.path.join(base_root, session_id)
            if not os.path.exists(chat_file_path) or os.path.getsize(chat_file_path) == 0:
                if os.path.exists(history_path):
                    try:
                        os.remove(history_path)
                    except Exception:
                        pass
                logger.info(f"{YELLOW}        [SURA History] Target chat file was deleted or reset. Initialized clean session: {session_id}{CLS}")
                return []

            if os.path.exists(history_path):
                try:
                    if os.path.getmtime(chat_file_path) > os.path.getmtime(history_path):
                        os.remove(history_path)
                        logger.info(f"{YELLOW}        [SURA History] Stale history detected for recreated chat file {session_id}. Resetting session.{CLS}")
                        return []
                except Exception:
                    pass

        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    chat_history = data.get("history", [])
                logger.info(f"{GREEN}        [SURA History] Restored continuous chat track for session: {session_id}{CLS}")
            except Exception as e:
                logger.error(f"{BOLD_RED}        [SURA History] Session load fallback triggered: {e}{CLS}")
                chat_history = []
        return chat_history

    def save_history(self, session_id: str, chat_history: list) -> list:
        # Truncate if too long before saving
        if len(chat_history) > self.max_history_turns:
            chat_history = [chat_history[0]] + chat_history[-8:]
            
        try:
            history_path = self.get_history_filepath(session_id)
            payload = {
                "session_id": session_id,
                "last_updated": time.time(),
                "history": chat_history
            }
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            logger.error(f"{BOLD_RED}        [SURA History] Session serialization failure: {e}{CLS}")
        
        return chat_history

    def cleanup_orphaned_histories(self):
        base_root = os.path.abspath(os.path.expanduser(detector.get_server_root()))
        if not os.path.exists(base_root):
            return

        search_pattern = os.path.join(base_root, ".sura_history_*.json")
        history_files = glob.glob(search_pattern)

        try:
            active_chat_files = set(f for f in os.listdir(base_root) if f.endswith('.chat'))
        except Exception as e:
            logger.error(f"{BOLD_RED}        [SURA Sweeper] Directory read failure: {e}{CLS}")
            return

        for hist_file in history_files:
            filename = os.path.basename(hist_file)
            if "default_chat_session" in filename:
                continue
                
            try:
                with open(hist_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    session_id = data.get("session_id", "")
                
                if session_id.endswith(".chat"):
                    if session_id not in active_chat_files:
                        os.remove(hist_file)
                        logger.info(f"{YELLOW}        [SURA Sweeper] Cleaned up history for deleted chat: {filename}{CLS}")
                else:
                    os.remove(hist_file)
                    logger.info(f"{YELLOW}        [SURA Sweeper] Purged temporary UUID history file: {filename}{CLS}")
            except Exception as e:
                logger.error(f"{BOLD_RED}        [SURA Sweeper] Sweeper error parsing {hist_file}: {e}{CLS}")
