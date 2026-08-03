"""
SURA Agent - Error Watcher (Kernel Side)

This module is dynamically injected into running IPython notebook kernels by the 
JupyterLab frontend extension. It hooks into IPython's `post_run_cell` event to 
monitor consecutive cell failures. When the threshold is reached, it:
1. Optionally displays a Markdown nudge directly in the notebook output.
2. Writes an error event payload to disk (`~/.duck_events/event.json`) which is 
   then picked up by the Chat Agent backend to provide proactive LLM assistance.
"""
import json
import os
import sys
import time
import traceback
from pathlib import Path

from IPython.display import display, Markdown

EVENT_DIR = Path.home() / ".duck_events"
EVENT_FILE = EVENT_DIR / "event.json"
CONFIG_FILE = EVENT_DIR / "config.json"

NUDGE = (
    "### ☕ Time for a quick breather?\n\n"
    "*Looks like this bug is being stubborn. Step away for 2 minutes, "
    "grab some water, and come back fresh! Check the chat panel — "
    "**@LocalAI** has a note for you.* 🦆"
)

class SocialEmotionalMentor:
    def __init__(self, threshold=3):
        self.threshold = threshold
        self.consecutive_failures = 0

    def check_cell_status(self, result):
        try:
            error = getattr(result, "error_in_exec", None)
            if error is None:
                error = getattr(result, "error_before_exec", None)

            if error is None:
                self.consecutive_failures = 0
                return

            self.consecutive_failures += 1
            if self.consecutive_failures < self.threshold:
                return
            self.consecutive_failures = 0

            # 1. Read frontend user preference (defaults to True if config doesn't exist)
            inline_enabled = True
            if CONFIG_FILE.exists():
                try:
                    cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                    inline_enabled = cfg.get("enable_inline_nudge", True)
                except Exception:
                    pass

            # 2. In-cell nudge display (only if inline nudges are enabled by user)
            if inline_enabled:
                display(Markdown(NUDGE))

            # 3. Write the event payload for the SURA Chat Agent / LocalPersona backend watcher
            tb = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            payload = {
                "timestamp": time.time(),  # persona uses this to dedupe/seed
                "threshold": self.threshold,
                "error_type": type(error).__name__,
                "traceback": tb[-2000:],  # keep payload size bounded
                "cell_source": getattr(
                    getattr(result, "info", None), "raw_cell", ""
                )[:2000],
                "displayed_message": NUDGE if inline_enabled else "",
            }
            self._write_event(payload)

        except Exception as e:
            print(f"[SEM] Callback error: {e}", file=sys.stderr)

    @staticmethod
    def _write_event(payload):
        """Atomic write so the persona never reads a half-written file."""
        EVENT_DIR.mkdir(exist_ok=True)
        tmp = EVENT_DIR / f".event.{os.getpid()}.tmp"
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(EVENT_FILE)


def setup_watcher():
    """
    Registers the error watcher hook dynamically into the current IPython kernel.
    Called by the JupyterLab frontend extension upon notebook readiness.
    """
    try:
        ip = get_ipython()  # noqa: F821
        
        # 1. Confirm running inside a Jupyter notebook kernel (not terminal IPython)
        is_jupyter = ip is not None and (
            ip.__class__.__name__ == "ZMQInteractiveShell" or "IPKernelApp" in sys.modules
        )

        if is_jupyter:
            # Unregister stale instances upon kernel restarts to avoid duplicates
            stale = [
                cb
                for cb in list(ip.events.callbacks.get("post_run_cell", []))
                if hasattr(cb, "__self__") and isinstance(cb.__self__, SocialEmotionalMentor)
            ]
            for cb in stale:
                ip.events.unregister("post_run_cell", cb)

            watcher = SocialEmotionalMentor(threshold=3)
            ip.events.register("post_run_cell", watcher.check_cell_status)
            print("✨ Error watcher hook successfully injected into kernel.")
    except Exception as e:
        print(f"Error initializing watcher: {e}", file=sys.stderr)
