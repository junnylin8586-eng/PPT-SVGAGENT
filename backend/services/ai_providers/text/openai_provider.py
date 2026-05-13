"""
OpenAI SDK implementation for text generation
"""
import base64
import logging
from typing import Generator
from openai import OpenAI
from .base import TextProvider, strip_think_tags

logger = logging.getLogger(__name__)


class OpenAITextProvider(TextProvider):
    """Text generation using OpenAI SDK (OpenAI-compatible endpoints)"""

    def __init__(self, api_key: str, api_base: str = None, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key, base_url=api_base, timeout=120, max_retries=2)
        self.model = model

    def generate_text(self, prompt: str, thinking_budget: int = 0) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return strip_think_tags(response.choices[0].message.content)

    def generate_text_stream(self, prompt: str, thinking_budget: int = 0) -> Generator[str, None, None]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    def generate_with_image(self, prompt: str, image_path: str, thinking_budget: int = 0) -> str:
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("ascii")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
                ],
            }],
        )
        content = response.choices[0].message.content
        return strip_think_tags(content if isinstance(content, str) else "\n".join(
            item.get("text") for item in (content or []) if item.get("text")
        ))