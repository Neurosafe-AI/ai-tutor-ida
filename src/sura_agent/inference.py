"""
SURA Agent - Inference Engine

This module abstracts the calls to the underlying Language Model (LLM) using the `litellm` library.
It is responsible for:
1. Sending the complete system prompt and chat history to the configured LLM.
2. Parsing the LLM response to separate the natural language answer from the structural "[SUGGESTIONS]".
3. Generating the raw HTML payload for the "Quick Reply" buttons and injecting them into the chat output.
4. Implementing retry logic if the model fails to return the required structural output format.
"""
import asyncio
import html
import re
import json
from pathlib import Path
import litellm
from .logger import logger, MAGENTA, YELLOW, CLS

CONFIG_FILE = Path.home() / ".duck_events" / "config.json"

def get_llm_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                model = data.get("llm_model", "ollama/qwen2.5-coder:1.5b")
                api_key = data.get("api_key", "")
                # Backwards compat mapping
                if model == "qwen2.5-coder:1.5b":
                    model = "ollama/qwen2.5-coder:1.5b"
                return model, api_key
        except Exception:
            pass
    return "ollama/qwen2.5-coder:1.5b", ""

class InferenceEngine:
    def __init__(self):
        self.max_retries = 3

    async def generate_response(self, chat_history, persona_name: str, frustration_flag: str) -> str:
        agent_output = ""
        final_suggestions = []
        valid_suggestions = []
        guiding_phrase = "How do you want to approach this next?"

        model_name, api_key = get_llm_config()

        for attempt in range(self.max_retries):
            kwargs = {
                "model": model_name,
                "messages": chat_history
            }
            if api_key and api_key.strip() != "":
                kwargs["api_key"] = api_key.strip()

            try:
                response = await litellm.acompletion(**kwargs)
                agent_output = response.choices[0].message.content or ""
            except Exception as e:
                logger.error(f"[Litellm API Error] {e}")
                agent_output = f"I encountered an error connecting to the model API: {e}. Please check your Agent Settings."
                break
            
            # Sanitization
            agent_output = re.sub(r'\[CRITICAL REMINDER:.*?\]', '', agent_output, flags=re.DOTALL)
            agent_output = re.sub(r'CRITICAL FORMATTING INSTRUCTIONS.*?\n', '', agent_output, flags=re.DOTALL)
            agent_output = re.sub(r'(?i)\bPART 1:\s*', '', agent_output)
            agent_output = re.sub(r'(?i)\*\*PART 1:\*\*\s*', '', agent_output).strip()

            suggestions = []
            parts = re.split(r'(?i)(?:\[SUGGESTIONS\]|PART 2:|\*\*PART 2:\*\*)', agent_output, maxsplit=1)
            agent_output = parts[0].strip()
            
            if len(parts) > 1:
                raw_lines_content = parts[1].strip()
                raw_lines = raw_lines_content.split('\n')
                for line in raw_lines:
                    cleaned = re.sub(r'^(?:Option\s*\d+:?|\d+\.?|Action Step \d+:?|Technical Step \d+:?|-|\*|•|Here are.*?options:?)\s*', '', line.strip(), flags=re.IGNORECASE).strip()
                    cleaned = cleaned.strip('"\'')
                    if cleaned and not re.match(r'(?i)^here are', cleaned):
                        suggestions.append(cleaned)

            if agent_output.startswith("```") and agent_output.endswith("```"):
                agent_output = re.sub(r'^```[a-zA-Z]*\n', '', agent_output)
                agent_output = re.sub(r'\n```$', '', agent_output).strip()
            elif agent_output.startswith("```"):
                agent_output = re.sub(r'^```[a-zA-Z]*\n', '', agent_output).strip()

            if not agent_output or len(agent_output.strip()) < 3:
                agent_output = "I've analyzed the request and your files. Here are some suggested next steps you can take:"

            valid_suggestions = []
            for item in suggestions:
                cleaned_item = re.sub(r'^\*{0,2}(?:Option\s*\d+:?|\d+\.?|Action Step \d+:?|Technical Step \d+:?)\*{0,2}\s*', '', item, flags=re.IGNORECASE).strip()
                if cleaned_item and cleaned_item not in valid_suggestions:
                    if len(cleaned_item.split()) > 10:
                        cleaned_item = " ".join(cleaned_item.split()[:10]) + "..."
                    valid_suggestions.append(cleaned_item)

            if len(valid_suggestions) >= 3:
                final_suggestions = valid_suggestions[:3]
                break
            else:
                logger.warning(f"{YELLOW}  [SURA Validation] Attempt {attempt + 1} failed: Found {len(valid_suggestions)} valid suggestions instead of 3. Retrying...{CLS}")
                await asyncio.sleep(1)

        default_tech_1 = "Inspect active notebook & debug cell errors"
        default_tech_2 = "Explain repository architecture and component dependencies"
        default_wellbeing = "Take a 2-minute mindful breather and stretch"

        if frustration_flag == "True":
            default_wellbeing = "Step away for 2 minutes and take a relaxing breather"

        if not final_suggestions or len(final_suggestions) < 3:
            final_suggestions = []
            if len(valid_suggestions) >= 1:
                final_suggestions.append(valid_suggestions[0])
            else:
                final_suggestions.append(default_tech_1)

            if len(valid_suggestions) >= 2:
                final_suggestions.append(valid_suggestions[1])
            else:
                final_suggestions.append(default_tech_2)
                
            if len(valid_suggestions) >= 3:
                final_suggestions.append(valid_suggestions[2])
            else:
                final_suggestions.append(default_wellbeing)

        button_html = f"\n\n---\n*{guiding_phrase}*\n\n<div class=\"sura-quick-reply-wrapper\">"
        persona_class_token = f"sura-persona-{persona_name}"

        for option in final_suggestions:
            safe_option = html.escape(option)
            button_html += (
                f'<button class="sura-quick-reply-btn {persona_class_token}" '
                f'data-prompt="{safe_option}" '
                f'title="{safe_option}">'
                f'{safe_option}'
                f'</button>'
            )
        button_html += "</div>"
        agent_output += button_html

        return agent_output
