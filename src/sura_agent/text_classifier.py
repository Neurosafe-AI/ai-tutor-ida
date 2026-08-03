from ollama import AsyncClient


class LLMTextClassifier:
    """Lightweight classification pass to optimize response depth and classify query intent."""
    def __init__(self, model_name: str = "qwen2.5-coder:1.5b"):
        self.model_name = model_name

    async def classify_text(self, text: str) -> str:
        """Evaluates text tone for affective routing."""
        lowered = text.lower()
        frustration_triggers = ["stuck", "error", "hate", "wtf", "broken", "why doesn't this work"]
        if any(trigger in lowered for trigger in frustration_triggers):
            return "anger"
        return "neutral"

    async def is_code_query(self, user_text: str) -> bool:
        if len(user_text.strip().split()) <= 3 and user_text.lower().strip("!.") in ["hi", "hello", "hey", "thanks"]:
            return False

        prompt = (
            "Determine if the following input requires code inspection, file reading, "
            "or notebook execution. Reply ONLY with 'TRUE' or 'FALSE'.\n\n"
            f"User input: {user_text}"
        )
        try:
            response = await AsyncClient().chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response['message']['content'].strip().upper()
            return "TRUE" in content
        except Exception:
            return True