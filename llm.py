import anthropic
from enum import Enum
from pathlib import Path
from utils.utils import json_parser


open_router_config = json_parser(Path("open-router-api-key.json"))
OPENROUTER_API_KEY = open_router_config["OPENROUTER_API_KEY"]
OPENROUTER_BASE_URL = open_router_config["OPENROUTER_BASE_URL"]


# ── LLM ─────────────────────────────────────────────────────────────────────
class LLMCenter:
    """Handles all API calls. No task or agent logic here."""

    MODELS = {
        "claude-sonnet": "anthropic/claude-sonnet-4-6",
        "claude-opus": "anthropic/claude-opus-4-6",
        "claude-haiku": "anthropic/claude-haiku-3-5",
        "gpt-4o": "openai/gpt-4o",
        "gpt-4o-mini": "openai/gpt-4o-mini",
        "o3-mini": "openai/o3-mini",
        "gemini-pro": "google/gemini-pro-1.5",
        "gemini-flash": "google/gemini-flash-1.5",
        "llama-70b": "meta-llama/llama-3.1-70b-instruct",
        "llama-405b": "meta-llama/llama-3.1-405b-instruct",
        "mistral-large": "mistralai/mistral-large",
        "mistral-small": "mistralai/mistral-small",
        "deepseek-chat": "deepseek/deepseek-chat",
        "deepseek-r1": "deepseek/deepseek-r1",
    }

    def __init__(
        self,
        api_key: str = OPENROUTER_API_KEY,
        base_url: str = OPENROUTER_BASE_URL,
        max_tokens: int = 8192,
    ):
        self.client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        self.max_tokens = max_tokens

    def resolve_model(self, model: str) -> str:
        return self.MODELS.get(model, model)

    def complete(self, model: str, system: str, user_input: str) -> str:
        response = self.client.messages.create(
            model=self.resolve_model(model),
            max_tokens=self.max_tokens,
            system=[
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ],
            messages=[{"role": "user", "content": user_input}],
        )
        return response.content[0].text

    def stream(self, model: str, system: str, user_input: str) -> str:
        """Stream response, printing tokens live. Returns full text when done."""
        full_text = []

        with self.client.messages.stream(
            model=self.resolve_model(model),
            max_tokens=self.max_tokens,
            system=[
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ],
            messages=[{"role": "user", "content": user_input}],
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
                full_text.append(text)

        print()
        return "".join(full_text)


llmCenter = LLMCenter(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)


if __name__ == "__main__":
    result1 = llmCenter.complete("claude-sonnet", "You are helpful.", "Hello!")
    print(f"Claude: {result1}")

    result2 = llmCenter.complete("gpt-4o", "You are helpful.", "Hello!")
    print(f"GPT: {result2}")
