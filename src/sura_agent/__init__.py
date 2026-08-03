from .handlers import setup_handlers

def _jupyter_server_extension_points():
    return [{"module": "sura_agent"}]

def _load_jupyter_server_extension(serverapp):
    """Triggers automatically when the user boots up Jupyter Lab."""
    setup_handlers(serverapp.web_app)

# HOOK: This tells JupyterLab where your compiled JavaScript lives
def _jupyter_labextension_paths():
    return [{
        "src": "labextension",
        "dest": "sura-agent"
    }]