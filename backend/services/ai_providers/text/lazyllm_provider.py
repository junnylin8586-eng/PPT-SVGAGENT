"""
LazyLLM text provider - routes to various LazyLLM vendors
"""
import os
import logging
from typing import Generator
from .base import TextProvider, strip_think_tags

logger = logging.getLogger(__name__)


def _get_key_for_source(source: str) -> str:
    """Get API key for LazyLLM vendor from env or settings."""
    upper = source.upper()
    key = os.getenv(f'{upper}_API_KEY', '')
    if key and key not in ('', 'your-key-here'):
        return key
    if source == 'minimax':
        for k in ['MINIMAX_CN_API_KEY', 'MINIMAX_API_KEY']:
            v = os.getenv(k, '')
            if v and v != 'your-key-here':
                return v
    return os.getenv('OPENAI_API_KEY', '')


class LazyLLMTextProvider(TextProvider):
    """Text generation via LazyLLM multi-vendor framework"""

    def __init__(self, source: str = 'deepseek', model: str = None):
        self.source = source
        self.model = model or f"{source}-default"
        self.api_key = _get_key_for_source(source)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError("openai package required for LazyLLM provider")
            base_urls = {
                'qwen': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                'deepseek': 'https://api.deepseek.com/v1',
                'doubao': 'https://ark.cn-beijing.volces.com/api/v3',
                'glm': 'https://open.bigmodel.cn/api/paas/v4',
                'kimi': 'https://api.moonshot.cn/v1',
            }
            base = base_urls.get(self.source, 'https://api.openai.com/v1')
            self._client = OpenAI(api_key=self.api_key, base_url=base)
        return self._client

    def generate_text(self, prompt: str, thinking_budget: int = 0) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return strip_think_tags(response.choices[0].message.content or '')

    def generate_text_stream(self, prompt: str, thinking_budget: int = 0) -> Generator[str, None, None]:
        client = self._get_client()
        for chunk in client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        ):
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content