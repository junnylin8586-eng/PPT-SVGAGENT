"""
MiniMax text provider (OpenAI-compatible API)
"""
import logging
from typing import Generator
from openai import OpenAI
from .base import TextProvider, strip_think_tags

logger = logging.getLogger(__name__)


class MiniMaxTextProvider(TextProvider):
    """Text generation using MiniMax API (OpenAI-compatible format)"""

    def __init__(self, api_key: str, api_base: str = None, model: str = "MiniMax-M2.7"):
        if not api_base:
            api_base = "https://api.minimax.chat/v1"
        self.client = OpenAI(api_key=api_key, base_url=api_base, timeout=120, max_retries=2)
        self.model = model

    def generate_text(self, prompt: str, thinking_budget: int = 0) -> str:
        """Generate text with MiniMax model."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        if content is None:
            return ""
        return strip_think_tags(content)

    def generate_text_messages(self, messages: list, thinking_budget: int = 0) -> str:
        """
        Generate text with a list of messages (multi-turn conversation).
        messages: [{"role": "user"|"assistant"|"system", "content": "..."}]
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        content = response.choices[0].message.content
        if content is None:
            return ""
        return strip_think_tags(content)

    def generate_text_stream(self, prompt: str, thinking_budget: int = 0) -> Generator[str, None, None]:
        """Stream text with MiniMax model."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content