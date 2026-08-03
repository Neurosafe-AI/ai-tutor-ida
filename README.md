# SURA Agent for JupyterLab

SURA Agent is a stateful, emotionally-aware programming assistant designed specifically for JupyterLab. It bridges the gap between static LLM chat interfaces and the dynamic reality of notebook development by combining structural code context with behavioral telemetry (like frustration detection and continuous error tracking).

## Core Features

- **Dynamic Kernel Error Watcher (`error_watcher.py`)**: Automatically monitors your notebook execution cells. If it detects consecutive code failures, it injects a "Mindful Breather" nudge directly into your notebook output to help you avoid debugging fatigue.
- **Contextual File Awareness (`context.py`)**: Seamlessly reads your active workspace files, automatically strips out raw Jupyter JSON, and injects clean code into the LLM's context window.
- **Persistent Chat History (`history.py`)**: Jupyter AI often loses context on reload. SURA Agent persists your chat history directly to `.sura_history_*.json` files locally, ensuring the agent always remembers the conversation.
- **Agent Settings UI (`settingWidget.tsx`)**: A custom-built floating UI panel accessible from the top menu that allows you to instantly switch models (Local Ollama vs Cloud API), configure API keys, and change the Agent's Persona (e.g., Strict Instructor, Empathetic Friend).
- **Quick Reply Suggestions (`quickActions.tsx`)**: The model automatically generates context-aware, clickable action buttons at the bottom of its responses (e.g., "Debug this cell", "Take a break") that map directly to complex prompt chains.

## Project Structure

The project is split into two halves:

### 1. The JupyterLab Frontend Extension (`src/frontend`)
Written in TypeScript and React. This code runs in the browser.
- **`index.tsx`**: The main entry point. Registers the top menu bar, the notebook toolbar switches, and silently injects the Python error watcher into running kernels.
- **`settingWidget.tsx`**: The React component for the Agent Settings expandable panel.
- **`quickActions.tsx`**: A DOM observer that forcefully injects the "Debug", "Explain", and "Take Break" buttons into the Jupyter AI chat interface.
- **`configAPI.ts`**: The REST API client that talks to our Python backend to persist settings.

### 2. The Jupyter Server Python Extension (`src/sura_agent`)
Written in Python. This code runs on the backend server.
- **`personas.py`**: The brain of the operation. Implements the `LocalPersona`, processes incoming messages, builds the dynamic system prompts, and handles the `litellm` inference calls.
- **`handlers.py`**: Tornado REST API endpoints (e.g., `/config`, `/models`) that the frontend uses.
- **`error_watcher.py`**: The IPython kernel hook that monitors for cell execution exceptions.
- **`history.py` & `context.py`**: Utilities for persisting chat state and reading workspace files.
- **`inference.py`**: LLM API wrappers.

## Building & Installation

To build the project locally for development:

1. Install dependencies:
   ```bash
   npm install
   pip install -e .
   ```

2. Build the frontend extension:
   ```bash
   npm run build
   ```

3. Restart your JupyterLab server so the Python backend picks up the changes:
   ```bash
   jupyter lab
   ```

## Requirements
- JupyterLab >= 4.0.0
- `jupyter-ai`
- `litellm`
- Local `ollama` (if using local models)
