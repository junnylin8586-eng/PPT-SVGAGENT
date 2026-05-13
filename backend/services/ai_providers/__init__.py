"""
AI Provider Registry for PPT Agent
Supports: MiniMax (OpenAI-compatible), OpenAI, Anthropic, Gemini
"""
import os
import logging
from typing import Optional
from .text import TextProvider, OpenAITextProvider, GenAITextProvider, AnthropicTextProvider
from .text.minimax_provider import MiniMaxTextProvider

logger = logging.getLogger(__name__)

# LazyLLM vendor names
LAZYLLM_VENDORS = {'qwen', 'doubao', 'deepseek', 'glm', 'siliconflow', 'sensenova', 'minimax', 'kimi'}


def get_provider_format() -> str:
    """Get configured provider format. Priority: Settings DB > env > 'openai'."""
    from flask import current_app
    try:
        if current_app and hasattr(current_app, 'config'):
            v = current_app.config.get('AI_PROVIDER_FORMAT')
            if v:
                return str(v).lower()
    except RuntimeError:
        pass
    return os.getenv('AI_PROVIDER_FORMAT', 'openai').lower()


def _resolve_setting(key: str, fallback: Optional[str] = None) -> Optional[str]:
    """Look up config: Flask app.config (Settings DB) > env > fallback."""
    try:
        from flask import current_app
        if current_app and hasattr(current_app, 'config'):
            v = current_app.config.get(key)
            if v is not None:
                return str(v)
    except RuntimeError:
        pass
    return os.getenv(key) or fallback


def _get_settings_api_key() -> Optional[str]:
    """Get API key: Settings DB > MINIMAX_API_KEY env > config default."""
    from models.settings import Settings
    settings = Settings.query.first()
    if settings and settings.api_key:
        return settings.api_key
    import os, importlib.util
    spec = importlib.util.spec_from_file_location('config',
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.py"))
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    return getattr(cfg, "MINIMAX_API_KEY", None) or None


def _get_settings_api_base() -> str:
    """Get API base URL: Settings DB > MINIMAX_API_BASE env > config default."""
    from models.settings import Settings
    settings = Settings.query.first()
    if settings and settings.api_base_url:
        return settings.api_base_url
    import os, importlib.util
    spec = importlib.util.spec_from_file_location('config',
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.py"))
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    return getattr(cfg, "MINIMAX_API_BASE", "https://api.minimax.chat/v1")

def get_text_provider(model: Optional[str] = None) -> TextProvider:
    """
    Factory: return appropriate text provider based on Settings DB / env.

    Supports:
      - openai (MiniMax / OpenAI-compatible): uses api_key + api_base_url
      - gemini: uses GOOGLE_API_KEY + GOOGLE_API_BASE
      - anthropic: uses ANTHROPIC_API_KEY + ANTHROPIC_API_BASE
      - lazyllm vendor (qwen, deepseek, doubao, kimi, minimax...)
    """
    fmt = get_provider_format()
    api_key = _get_settings_api_key()
    api_base = _get_settings_api_base()
    model = model or 'MiniMax-M2.7'

    if fmt == 'minimax' or (fmt == 'openai' and 'minimax' in api_base.lower()):
        logger.info(f"Text provider: MiniMax, model={model}, api_base={api_base}")
        return MiniMaxTextProvider(api_key=api_key, api_base=api_base, model=model)

    if fmt == 'openai':
        logger.info(f"Text provider: OpenAI-compatible, model={model}")
        return OpenAITextProvider(
            api_key=api_key,
            api_base=api_base,
            model=model,
        )

    if fmt == 'gemini':
        google_key = _resolve_setting('GOOGLE_API_KEY') or api_key
        google_base = _resolve_setting('GOOGLE_API_BASE', '')
        logger.info(f"Text provider: Gemini, model={model}")
        return GenAITextProvider(api_key=google_key, api_base=google_base, model=model)

    if fmt == 'anthropic':
        anthropic_key = _resolve_setting('ANTHROPIC_API_KEY') or api_key
        anthropic_base = _resolve_setting('ANTHROPIC_API_BASE', 'https://api.anthropic.com')
        logger.info(f"Text provider: Anthropic, model={model}")
        return AnthropicTextProvider(api_key=anthropic_key, api_base=anthropic_base, model=model)

    if fmt in LAZYLLM_VENDORS:
        logger.info(f"Text provider: LazyLLM, vendor={fmt}, model={model}")
        from .text.lazyllm_provider import LazyLLMTextProvider
        return LazyLLMTextProvider(source=fmt, model=model)

    # Default fallback to MiniMax
    logger.info(f"Text provider: MiniMax (default), model={model}")
    return MiniMaxTextProvider(api_key=api_key, api_base=api_base, model=model)