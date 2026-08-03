# src/sura_agent/telemetry.py
import os
import json
import time
import re
from scipy.stats import mode

class FrustrationDetector:
    def __init__(self, window_size=120):
        self.window_size = window_size  
        self.input_buffer = []
        self.keystroke_history = []
        self.active_file = None        
        self.server_root = os.getcwd()
        self.server_port = os.getpid()

    def set_server_root(self, path):
        """Sets the absolute workspace root folder mapped by the active Jupyter server context."""
        if path:
            path = os.path.abspath(os.path.expanduser(path))
        self.server_root = path

    def get_server_root(self):
        """Exposes the absolute synchronized server root directory path."""
        if self.server_root:
            return os.path.abspath(os.path.expanduser(self.server_root))
        return os.getcwd()

    def set_server_port(self, port):
        """Sets the server port or process identifier for server isolation."""
        if port:
            self.server_port = str(port)

    def get_server_port(self):
        """Exposes the server port or process identifier."""
        return str(self.server_port or os.getpid())

    def log_event(self, event_type, data=None):
        """Buffers raw typing intervals and focus-state shifts."""
        timestamp = time.time()
        self.input_buffer.append({"type": event_type, "time": timestamp, "data": data})
        
        if event_type == "focus_change" and data and "file_path" in data:
            f_path = data["file_path"]
            if f_path and f_path.endswith(('.py', '.ipynb')) and not os.path.basename(f_path).startswith(('.~', '.')):
                self.active_file = f_path
        
        if event_type == "keystroke" and data and "latency" in data:
            lat = data["latency"]
            if lat <= 1.0: 
                self.keystroke_history.append(lat)
                if len(self.keystroke_history) > 10:
                    self.keystroke_history.pop(0)

    def compute_baseline(self):
        if len(self.keystroke_history) < 5:
            return 0.20 
        return sum(self.keystroke_history) / len(self.keystroke_history)

    def get_active_file(self):
        """Taps into Windows OS Window Title to capture active JupyterLab tabs.
        
        Falls back to last received focus_change telemetry event if unavailable.
        """
        try:
            import win32gui
            window = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(window)
            
            if "JupyterLab" in title:
                match = re.search(r'([\w\-\.]+\.(ipynb|py))', title)
                if match:
                    os_active_file = match.group(1)
                    root = self.get_server_root()
                    if os.path.exists(os.path.join(root, os_active_file)):
                        return os_active_file
        except ImportError:
            pass
        except Exception:
            pass
            
        return self.active_file

    def extract_paper_features(self):
        now = time.time()
        active_window = [e for e in self.input_buffer if now - e["time"] <= self.window_size]
        self.input_buffer = active_window 
        
        keystrokes = [e for e in active_window if e["type"] == "keystroke"]
        if len(keystrokes) < 5:
            return None 

        dwell_times = [e["data"]["latency"] for e in keystrokes if e["data"].get("latency")]
        baseline = self.compute_baseline()
        norm_dwells = [d / baseline for d in dwell_times] if baseline > 0 else dwell_times
        backspaces = [e for e in keystrokes if e["data"].get("key_name") in ["Backspace", "Delete"]]
        
        features = {
            "typing_speed": len(keystrokes) / (self.window_size / 60.0),
            "min_dwell": min(norm_dwells) if norm_dwells else 1.0,
            "mode_dwell": float(mode(norm_dwells, keepdims=True).mode[0]) if norm_dwells else 1.0,
            "backspace_freq": len(backspaces)
        }
        return self.discretize_features(features)

    def discretize_features(self, feat_dict):
        discretized = {}
        for k, v in feat_dict.items():
            if v == 0: discretized[k] = 1
            elif v < 2.0: discretized[k] = 2
            elif v < 4.0: discretized[k] = 3
            elif v < 7.0: discretized[k] = 4
            else: discretized[k] = 5
        return discretized

    def predict_keyboard_emotion(self):
        features = self.extract_paper_features()
        if not features:
            return "neutral"
        try:
            current_dir = os.path.dirname(__file__)
            json_path = os.path.join(current_dir, "assets", "model_cpt_weights.json")
            with open(json_path, "r", encoding="utf-8") as f:
                weights = json.load(f)["feature_sensitivities"]
            p_backspace = weights["backspace_freq"][f"bin_{features['backspace_freq']}"]
            p_speed = weights["typing_speed"][f"bin_{features['typing_speed']}"]
            score = (p_backspace * 0.7) + (p_speed * 0.3)
            return "anger" if score > 0.65 else "neutral"
        except Exception:
            return "neutral"

detector = FrustrationDetector(window_size=120)