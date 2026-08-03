"""
SURA Agent - Persona Manager

This module implements the core Jupyter AI Agent persona (`LocalPersona`).
It handles intercepting user chat messages, extracting active workspace context,
assessing emotional telemetry, constructing system prompts (roles), and 
calling the underlying LLM via the `InferenceEngine`.

It also runs a background asyncio task to poll for kernel errors emitted by the 
`error_watcher.py` kernel hook, delivering proactive emotional support messages.
"""
import os
import json
import time
import re
import asyncio
from pathlib import Path
from jupyter_ai_persona_manager import BasePersona, PersonaDefaults
from jupyterlab_chat.models import Message

from .telemetry import detector
from .text_classifier import LLMTextClassifier
from .logger import logger, BLUE, YELLOW, GREEN, MAGENTA, BOLD_RED, CLS
from .history import HistoryManager
from .context import ContextBuilder
from .inference import InferenceEngine

text_engine = LLMTextClassifier(model_name="qwen2.5-coder:1.5b")

CONFIG_FILE = Path.home() / ".duck_events" / "config.json"
EVENT_FILE = Path.home() / ".duck_events" / "event.json"
POLL_INTERVAL_SECONDS = 2.0

def is_inline_nudge_enabled() -> bool:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for key in ["enable_inline_nudge", "enable_mentor", "mentor_enabled"]:
                    if key in data:
                        return bool(data[key])
        except Exception as e:
            logger.error(f"{BOLD_RED}        [SURA Config] Error reading config.json: {e}{CLS}")
    return True

def get_agent_role() -> str:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("agent_role", "systems_architect")
        except Exception:
            pass
    return "systems_architect"

def get_role_prompt(role_key: str) -> str:
    prompts = {
        "systems_architect": (
            "You are an expert, autonomous tool-augmented systems architect and supportive programming mentor. "
            "You specialize in repository-level code analysis, component dependencies, and architectural mapping.\n\n"
        ),
        "teaching_assistant": (
            "You are a helpful Teaching Assistant. Your goal is to guide the student to the answer using Socratic "
            "questioning, rather than just handing them the code. Focus on core concepts and step-by-step logic.\n\n"
        ),
        "empathetic_friend": (
            "You are a highly empathetic, casual programming buddy. You speak conversationally, offer emotional support, "
            "and pair-program in a relaxed tone. You celebrate small wins and encourage the user.\n\n"
        ),
        "strict_instructor": (
            "You are a strict, formal Senior Instructor. You demand industry-standard best practices, high-quality "
            "documentation, and rigorous error handling. You point out inefficient or unpythonic code directly.\n\n"
        )
    }
    return prompts.get(role_key, prompts["systems_architect"])

class LocalPersona(BasePersona):
    _watcher_claimed = False

    @property
    def defaults(self):
        current_dir = os.path.dirname(__file__)
        avatar_file_path = os.path.join(current_dir, "assets", "avatar.svg")

        return PersonaDefaults(
            name="LocalAI",
            description="Stateful programming assistant with cross-file dependency resolution and real-time emotional mentor support.",
            avatar_path=avatar_file_path,
            system_prompt=(
                "You are an expert, autonomous tool-augmented systems architect and supportive programming mentor. "
                "You specialize in repository-level code analysis, component dependencies, and architectural mapping.\n\n"
                "CROSS-FILE WORKFLOW RULES:\n"
                "1. Review the 'AUTOMATED CONTEXT INJECTION' boundaries appended to the user prompt. "
                "If multiple files are loaded, analyze their imports, class relationships, and communication paths.\n"
                "2. If an injected file relies on a dependency module listed in 'ALL AVAILABLE WORKSPACE FILES' "
                "that was not pre-emptively injected, use your 'read_workspace_file' tool to inspect it immediately.\n"
                "3. Always deliver your final architectural breakdown as clean, scannable markdown text."
            )
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history_mgr = HistoryManager(max_history_turns=12)
        self.context_builder = ContextBuilder()
        self.inference_engine = InferenceEngine()
        
        self.chat_history = []
        self._watcher_task = None
        
        if not LocalPersona._watcher_claimed:
            LocalPersona._watcher_claimed = True
            try:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.get_event_loop()

                if loop and loop.is_running():
                    self._watcher_task = loop.create_task(self._watch_for_kernel_errors())
                    logger.info(f"{GREEN}        [SURA Emotional Mentor] Active kernel error watcher task initiated.{CLS}")
                elif loop:
                    loop.call_soon(lambda: asyncio.create_task(self._watch_for_kernel_errors()))
                    logger.info(f"{GREEN}        [SURA Emotional Mentor] Scheduled kernel error watcher task.{CLS}")
            except Exception as e:
                logger.warning(f"{YELLOW}        [SURA Emotional Mentor] Kernel watcher init deferred: {e}{CLS}")

    async def shutdown(self) -> None:
        if self._watcher_task and not self._watcher_task.done():
            self._watcher_task.cancel()
            logger.info(f"{YELLOW}        [SURA Emotional Mentor] Kernel watcher task cancelled during shutdown.{CLS}")
        LocalPersona._watcher_claimed = False
        await super().shutdown()

    async def _watch_for_kernel_errors(self):
        last_event_id = None
        if EVENT_FILE.exists():
            try:
                with open(EVENT_FILE, "r", encoding="utf-8") as f:
                    last_event_id = json.load(f).get("timestamp")
            except Exception:
                pass

        while True:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            try:
                if not EVENT_FILE.exists():
                    continue
                
                with open(EVENT_FILE, "r", encoding="utf-8") as f:
                    event = json.load(f)

                event_id = event.get("timestamp")
                if event_id is None or event_id == last_event_id:
                    continue

                last_event_id = event_id

                if not is_inline_nudge_enabled():
                    logger.info(f"{YELLOW}        [SURA Emotional Mentor] Error threshold reached, but inline nudges are toggled OFF.{CLS}")
                    continue

                threshold = event.get('threshold', 3)
                error_type = event.get('error_type', 'Error')
                
                support_msg = (
                    f"🧘 **Mindful Minute**\n\n"
                    f"I noticed your notebook code hit {threshold} consecutive execution errors ({error_type}). "
                    f"Debugging can be mentally exhausting! Step away for two minutes, grab some water, and take a quick breather. "
                    f"When you're ready, let me know if you want to inspect the error together!"
                )
                
                logger.info(f"{YELLOW}        [SURA Emotional Mentor] Consecutive error threshold hit! Dispatched break invitation.{CLS}")
                self.send_message(support_msg)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"{BOLD_RED}        [SURA Error Watcher] Exception: {e}{CLS}")

    def _read_last_kernel_event(self):
        try:
            if EVENT_FILE.exists():
                with open(EVENT_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def _log_interaction_telemetry(self, clean_prompt, agent_output, keyboard_emo, text_emo, frustration, focus_file):
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "epoch_time": time.time(),
            "active_file_focus": focus_file if focus_file else "None",
            "user_prompt": clean_prompt,
            "agent_response": agent_output,
            "labels": {
                "keyboard_inferred_emotion": keyboard_emo,
                "text_inferred_emotion": text_emo,
                "frustration_ensemble_detected": frustration
            }
        }
        logger.info(json.dumps(log_entry))
        logger.info(f"{GREEN}        [SURA Telemetry] Interaction successfully logged.{CLS}")

    async def process_message(self, message: Message):
        if message.sender == self.id:
            return

        clean_prompt = message.body.replace("@LocalAI", "").strip()
        logger.info(f"\n{MAGENTA}[Stateful LocalAI Backend] Processing incoming message...{CLS}")

        self.history_mgr.cleanup_orphaned_histories()

        telemetry_focus_file = detector.get_active_file()
        focus_override_match = re.search(r'(?:\[focus:\s*|<!--\s*focus:\s*)(.*?)(?:\]|\s*-->)', clean_prompt)
        if focus_override_match:
            telemetry_focus_file = focus_override_match.group(1).strip()
            clean_prompt = re.sub(r'(?:\[focus:\s*|<!--\s*focus:\s*).*?(?:\]|\s*-->)', '', clean_prompt).strip()
            logger.info(f"{YELLOW}        [SURA Context] Focus override detected via quick-reply: {telemetry_focus_file}{CLS}")

        keyboard_emotion = detector.predict_keyboard_emotion()
        text_emotion = await text_engine.classify_text(clean_prompt)
        frustration_flag = "True" if (keyboard_emotion == "anger" and text_emotion == "anger") else "False"
        
        kernel_event = self._read_last_kernel_event()
        kernel_context_str = "None"
        if kernel_event and (time.time() - kernel_event.get("timestamp", 0)) < 300:
            kernel_context_str = (
                f"Recent Consecutive Failure Count: {kernel_event.get('threshold')}, "
                f"Error Type: {kernel_event.get('error_type')}, "
                f"Failed Cell Snippet: {kernel_event.get('cell_source', '')[:200]}"
            )

        all_workspace_assets = self.context_builder.list_workspace_files()
        
        matched_files = []
        for asset in all_workspace_assets:
            file_stem = os.path.splitext(os.path.basename(asset))[0]
            if asset.lower() in clean_prompt.lower() or file_stem.lower() in clean_prompt.lower():
                matched_files.append(asset)

        code_keywords = ['explain', 'debug', 'code', 'notebook', 'cell', 'error', 'fix', 'review', 'analyze', 'understand', 'compile', 'run', 'syntax', 'script', 'file', 'connection', 'integrate', 'call', 'function', 'class', 'module']
        is_code_query = any(kw in clean_prompt.lower() for kw in code_keywords) or len(matched_files) > 0

        if is_code_query and not telemetry_focus_file and len(matched_files) == 0:
            base_root = os.path.abspath(os.path.expanduser(detector.get_server_root()))
            if os.path.exists(base_root):
                try:
                    workspace_files = [f for f in os.listdir(base_root) if f.endswith((".ipynb", ".py")) and not f.startswith((".", ".~"))]
                    if workspace_files:
                        workspace_files.sort(key=lambda x: os.path.getatime(os.path.join(base_root, x)), reverse=True)
                        telemetry_focus_file = workspace_files[0]
                except Exception:
                    pass

        logger.info(f"{BLUE}  Keyboard Inferred Emotion: {keyboard_emotion}{CLS}")
        logger.info(f"{BLUE}  Text Inferred Emotion: {text_emotion}{CLS}")
        logger.info(f"{BOLD_RED if frustration_flag == 'True' else BLUE}  Ensemble Frustration Detected: {frustration_flag}{CLS}")
        logger.info(f"{BLUE}  Kernel Error Event Context: {kernel_context_str}{CLS}")

        injected_payload = clean_prompt
        if is_code_query:
            if len(matched_files) > 0:
                logger.info(f"{BLUE}  Injecting referenced cross-file architectural modules...{CLS}")
                for asset in matched_files[:4]: 
                    file_contents = self.context_builder.read_and_cache_file(asset)
                    injected_payload += (
                        f"\n\n[AUTOMATED CONTEXT INJECTION - MODULE SOURCE: {asset}]\n"
                        f"{file_contents}"
                    )
            elif telemetry_focus_file:
                logger.info(f"{BLUE}  Injecting context data for active file window: {telemetry_focus_file}...{CLS}")
                file_contents = self.context_builder.read_and_cache_file(telemetry_focus_file)
                injected_payload += (
                    f"\n\n[AUTOMATED CONTEXT INJECTION - ACTIVE FILE Focus: {telemetry_focus_file}]\n"
                    f"{file_contents}"
                )

        cached_files_manifest = ", ".join(self.context_builder.file_cache.keys()) if self.context_builder.file_cache else "None"
        
        system_metadata = (
            f"--- REAL-TIME DEVELOPER TELEMETRY INTERFACE ---\n"
            f"frustration_detected: {frustration_flag}\n"
            f"recent_kernel_error_event: {kernel_context_str}\n"
            f"telemetry_inferred_focus_file: {telemetry_focus_file if telemetry_focus_file else 'None'}\n"
            f"ALL AVAILABLE WORKSPACE FILES: {all_workspace_assets}\n"
            f"ACTIVE SESSION WORKING MEMORY CACHE: [{cached_files_manifest}]\n"
            f"------------------------------------------------\n\n"
            f"CRITICAL FORMATTING INSTRUCTIONS FOR ACTION BUTTONS:\n"
            f"Your response MUST contain two parts:\n"
            f"PART 1: A thoughtful, conversational answer to the user's query. (Provide your actual answer here!)\n"
            f"PART 2: Exactly 3 quick-reply options appended at the very end of your response.\n\n"
            f"You MUST use the following exact format for the options block:\n\n"
            f"[SUGGESTIONS]\n"
            f"1. Inspect notebook for syntax errors\n"
            f"2. Explain repository architecture and dependencies\n"
            f"3. Take a 2-minute mindful breather\n\n"
            f"RULES FOR OPTIONS:\n"
            f"- Each option MUST be extremely short (MAXIMUM 8 WORDS).\n"
            f"- Option 1 MUST be a direct technical next step or debug option.\n"
            f"- Option 2 MUST be an alternative technical direction.\n"
            f"- Option 3 MUST be an EMOTIONAL SUPPORT / well-being step.\n"
            f"- You MUST include the exact literal text '[SUGGESTIONS]' before the options."
        )

        chat_session_id = self.history_mgr.get_chat_session_id(message)
        self.chat_history = self.history_mgr.load_history(chat_session_id)

        current_role_key = get_agent_role()
        role_prompt = get_role_prompt(current_role_key)
        
        full_system_prompt = (
            f"{role_prompt}"
            "CROSS-FILE WORKFLOW RULES:\n"
            "1. Review the 'AUTOMATED CONTEXT INJECTION' boundaries appended to the user prompt. "
            "If multiple files are loaded, analyze their imports, class relationships, and communication paths.\n"
            "2. If an injected file relies on a dependency module listed in 'ALL AVAILABLE WORKSPACE FILES' "
            "that was not pre-emptively injected, use your 'read_workspace_file' tool to inspect it immediately.\n"
            "3. Always deliver your final architectural breakdown as clean, scannable markdown text."
        )

        if len(self.chat_history) == 0:
            self.chat_history.append({'role': 'system', 'content': f"{full_system_prompt}\n\n{system_metadata}"})
        else:
            self.chat_history[0] = {'role': 'system', 'content': f"{full_system_prompt}\n\n{system_metadata}"}

        self.chat_history.append({'role': 'user', 'content': injected_payload})
        self.history_mgr.save_history(chat_session_id, self.chat_history)

        logger.info(f"{MAGENTA}  Executing Direct LocalAI Inference Pass...{CLS}")
        
        agent_output = await self.inference_engine.generate_response(
            self.chat_history, 
            self.defaults.name,
            frustration_flag
        )

        self.chat_history.append({'role': 'assistant', 'content': agent_output})
        self.chat_history = self.history_mgr.save_history(chat_session_id, self.chat_history)

        self._log_interaction_telemetry(
            clean_prompt, agent_output, 
            keyboard_emotion, text_emotion, 
            frustration_flag, telemetry_focus_file
        )

        self.send_message(agent_output)
        logger.info(f"{GREEN}[Stateful LocalAI Backend] Output successfully dispatched to chat layout.{CLS}\n")