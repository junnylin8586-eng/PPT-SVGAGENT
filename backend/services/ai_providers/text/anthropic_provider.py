"""
Anthropic Claude text provider
"""
import logging
from typing import Generator
from .base import TextProvider, strip_think_tags

logger = logging.getLogger(__name__)


class AnthropicTextProvider(TextProvider):
    """Text generation using Anthropic Claude"""

    def __init__(self, api_key: str, api_base: str = None, model: str = "claude-3-5-sonnet-20241014"):
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("anthropic not installed. Run: uv pip install anthropic")
        self.client = Anthropic(api_key=api_key, base_url=api_base)
        self.model = model

    def generate_text(self, prompt: str, thinking_budget: int = 0) -> str:
        extra = {}
        if thinking_budget > 0:
            extra["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            **extra
        )
        return strip_think_tags(response.content[0].text)

    def generate_text_stream(self, prompt: str, thinking_budget: int = 0) -> Generator[str, None, None]:
        extra = {}
        if thinking_budget > 0:
            extra["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
        with self.client.messages.stream(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            **extra
        ) as stream:
            for text in stream.text_stream:
                stripped = strip_think_tags(text)
                if stripped:
                    yield stripped