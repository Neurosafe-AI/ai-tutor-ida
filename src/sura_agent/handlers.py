"""
SURA Agent - Jupyter Server Extension Handlers

This module defines the REST API endpoints that the JupyterLab frontend extension uses
to communicate with the Python backend. 

Key responsibilities:
1. `/config`: Read/Write user preferences (model choice, threshold, role) to disk.
2. `/telemetry`: Receive UI telemetry for emotional inference.
3. `/models`: Expose litellm's exhaustive model list for the frontend datalist.
4. Windows File Handle Patch: Monkey-patches `FileContentsManager.rename_file` to handle
   race conditions specific to JupyterLab-Chat files on Windows.
"""
import os
import json
from pathlib import Path
from jupyter_server.base.handlers import APIHandler
from jupyter_server.services.contents.filemanager import FileContentsManager
from jupyter_server.utils import url_path_join
import tornado

CONFIG_FILE = Path.home() / ".duck_events" / "config.json"
EVENT_FILE = Path.home() / ".duck_events" / "event.json"

# Monkey-patch FileContentsManager.rename_file to handle pre-moved .chat files safely on Windows
_orig_rename_file = FileContentsManager.rename_file

async def _safe_rename_file(self, old_path, new_path):
    try:
        old_os_path = self._get_os_path(old_path)
        new_os_path = self._get_os_path(new_path)

        # If old_os_path no longer exists because ServerDocsApp/YDoc already moved it to new_os_path:
        if not os.path.exists(old_os_path) and os.path.exists(new_os_path):
            return
    except Exception:
        pass
    return await _orig_rename_file(self, old_path, new_path)

FileContentsManager.rename_file = _safe_rename_file


class ConfigRouteHandler(APIHandler):
    @tornado.web.authenticated
    def get(self):
        """Fetches the mentor configuration JSON."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.finish(json.dumps(data))
                return
            except Exception as e:
                self.log.error(f"[SURA Config] Read error: {e}")
        self.finish(json.dumps({"enable_inline_nudge": True}))

    @tornado.web.authenticated
    def post(self):
        """Updates the mentor configuration JSON."""
        data = self.get_json_body() or {}
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        current_config = {}
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    current_config = json.load(f)
            except Exception:
                pass

        current_config.update(data)

        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(current_config, f, indent=2)
            self.finish(json.dumps({"status": "ok", "config": current_config}))
        except Exception as e:
            self.set_status(500)
            self.finish(json.dumps({"error": str(e)}))


class TelemetryRouteHandler(APIHandler):
    @tornado.web.authenticated
    def post(self):
        """Receives client-side typing/interaction telemetry signals."""
        payload = self.get_json_body() or {}
        EVENT_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(EVENT_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            self.finish(json.dumps({"status": "received"}))
        except Exception as e:
            self.set_status(500)
            self.finish(json.dumps({"error": str(e)}))


import litellm

class ModelsRouteHandler(APIHandler):
    @tornado.web.authenticated
    def get(self):
        """Fetches the exhaustive list of models from litellm."""
        try:
            models = litellm.model_list if hasattr(litellm, 'model_list') else []
            self.finish(json.dumps(models))
        except Exception as e:
            self.log.error(f"[SURA Config] Error fetching litellm models: {e}")
            self.finish(json.dumps([]))

def setup_handlers(web_app):
    host_pattern = ".*$"
    base_url = web_app.settings["base_url"]

    config_route = url_path_join(base_url, "duck_events", "config")
    telemetry_route = url_path_join(base_url, "duck_events", "telemetry")
    models_route = url_path_join(base_url, "duck_events", "models")

    handlers = [
        (config_route, ConfigRouteHandler),
        (telemetry_route, TelemetryRouteHandler),
        (models_route, ModelsRouteHandler),
    ]
    web_app.add_handlers(host_pattern, handlers)