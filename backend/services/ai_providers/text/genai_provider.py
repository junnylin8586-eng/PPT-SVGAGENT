"""
Google Gemini text provider
"""
import logging
from typing import Generator
from .base import TextProvider, strip_think_tags

logger = logging.getLogger(__name__)


class GenAITextProvider(TextProvider):
    """Text generation using Google Gemini"""

    def __init__(self, api_key: str, api_base: str = None, model: str = "gemini-2.0-flash"):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("google-generativeai not installed. Run: uv pip install google-generativeai")
        self.client = genai
        self.client.api_key = api_key
        self.model_name = model

    def generate_text(self, prompt: str, thinking_budget: int = 0) -> str:
        model = self.client.GenerativeModel(self.model_name)
        generation_config = {}
        if thinking_budget > 0:
            generation_config["thinking_config"] = {"thinking_budget": thinking_budget}
        response = model.generate_content(prompt, generation_config=generation_config)
        return strip_think_tags(response.text)

    def generate_text_stream(self, prompt: str, thinking_budget: int = 0) -> Generator[str, None, None]:
        model = self.client.GenerativeModel(self.model_name)
        generation_config = {}
        if thinking_budget > 0:
            generation_config["thinking_config"] = {"thinking_budget": thinking_budget}
        for chunk in model.generate_content(prompt, generation_config=generation_config, stream=True):
            text = strip_think_tags(chunk.text)
            if text:
                yield text