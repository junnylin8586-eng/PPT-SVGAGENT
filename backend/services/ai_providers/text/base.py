"""
Abstract base class for text generation providers
"""
import re
from abc import ABC, abstractmethod
from typing import Generator, Optional


def strip_think_tags(text: str) -> str:
    """Remove <think>... blocks (including multiline) from AI responses."""
    if not text:
        return text
    return re.sub(r'<think>.*?\s*', '', text, flags=re.DOTALL).strip()


class TextProvider(ABC):
    """Abstract base class for text generation"""

    @abstractmethod
    def generate_text(self, prompt: str, thinking_budget: int = 0) -> str:
        """Generate text content from prompt."""
        pass

    def generate_text_messages(self, messages: list, thinking_budget: int = 0) -> str:
        """
        Generate text from a list of messages (multi-turn conversation).
        Default implementation wraps messages into a single prompt.
        Override in provider if the API supports native multi-turn.
        """
        prompt_parts = []
        for m in messages:
            role = m.get('role', 'user')
            content = m.get('content', '')
            if role == 'system':
                prompt_parts.append(f"[System] {content}")
            elif role == 'assistant':
                prompt_parts.append(f"[Assistant] {content}")
            else:
                prompt_parts.append(f"[User] {content}")
        return self.generate_text('\n'.join(prompt_parts), thinking_budget=thinking_budget)

    def generate_text_stream(self, prompt: str, thinking_budget: int = 0) -> Generator[str, None, None]:
        """Stream text content, yielding chunks. Default: non-streaming fallback."""
        yield self.generate_text(prompt, thinking_budget=thinking_budget)