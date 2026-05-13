"""
Settings Controller - AI API Key & Model Configuration
"""
import logging
from flask import Blueprint, request, jsonify

from models import db
from models.settings import Settings

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')


def success(data=None, code=200):
    r = {'success': True}
    if data is not None:
        r['data'] = data
    return jsonify(r), code


def err(msg, code=400):
    return jsonify({'success': False, 'error': msg}), code


@settings_bp.route('', methods=['GET'])
def get_settings():
    """GET /api/settings - 获取当前设置（含 API Key 长度掩码）"""
    try:
        settings = Settings.get_settings()
        return success(settings.to_dict())
    except Exception as e:
        logger.error(f"[Settings] GET failed: {e}")
        return err(str(e), 500)


@settings_bp.route('', methods=['PUT'])
def update_settings():
    """PUT /api/settings - 更新设置（AI Key / 模型 / Provider）"""
    try:
        data = request.get_json() or {}
        settings = Settings.get_settings()

        # AI Provider 配置
        if 'ai_provider_format' in data:
            settings.ai_provider_format = data['ai_provider_format']
        if 'api_base_url' in data:
            settings.api_base_url = data['api_base_url']
        if 'api_key' in data:
            settings.api_key = data['api_key'] if data['api_key'] else None

        # MiniMax 专用配置
        if 'minimax_api_key' in data:
            settings.minimax_api_key = data['minimax_api_key'] if data['minimax_api_key'] else None
        if 'minimax_api_base' in data:
            settings.minimax_api_base = data['minimax_api_base'] if data['minimax_api_base'] else None

        # 模型名称
        if 'text_model' in data:
            settings.text_model = data['text_model'] if data['text_model'] else None
        if 'image_model' in data:
            settings.image_model = data['image_model'] if data['image_model'] else None

        # Per-model sources
        if 'text_model_source' in data:
            settings.text_model_source = data['text_model_source'] or None
        if 'image_model_source' in data:
            settings.image_model_source = data['image_model_source'] or None

        # Per-model API 凭证
        for field in ['text_api_key', 'text_api_base_url',
                      'image_api_key', 'image_api_base_url',
                      'image_caption_api_key', 'image_caption_api_base_url']:
            if field in data:
                setattr(settings, field, data[field] if data[field] else None)

        # 图片生成配置
        if 'image_resolution' in data:
            settings.image_resolution = data['image_resolution']
        if 'image_aspect_ratio' in data:
            settings.image_aspect_ratio = data['image_aspect_ratio']

        db.session.commit()
        logger.info("[Settings] Updated successfully")

        # Reload app.config so changes take effect immediately
        from flask import current_app
        if current_app and hasattr(current_app, 'config'):
            _apply_settings_to_app(settings, current_app.config)

        return success(settings.to_dict())

    except Exception as e:
        db.session.rollback()
        logger.error(f"[Settings] PUT failed: {e}")
        return err(str(e), 500)


@settings_bp.route('/check', methods=['POST'])
def check_connection():
    """
    POST /api/settings/check - 验证 API Key 是否可用
    Body: { "api_key": "...", "api_base_url": "...", "provider": "minimax" }
    """
    try:
        data = request.get_json() or {}
        api_key = data.get('api_key', '')
        api_base = data.get('api_base_url', 'https://api.minimax.chat/v1')
        provider = data.get('provider', 'minimax')

        if not api_key:
            return err('api_key is required')

        from services.ai_providers import get_text_provider
        from services.ai_providers.text import MiniMaxTextProvider

        if provider == 'minimax':
            p = MiniMaxTextProvider(api_key=api_key, api_base=api_base, model='MiniMax-M2.7')
            result = p.generate_text('Say "OK" if you can read this.', thinking_budget=0)
            if 'OK' in result.upper():
                return success({'ok': True, 'message': 'API Key Valid'})
            return err(f'Unexpected response: {result[:50]}')

        return err(f'Unsupported provider: {provider}')

    except Exception as e:
        logger.error(f"[Settings] Connection check failed: {e}")
        return err(str(e), 500)


def _apply_settings_to_app(settings: Settings, config: dict):
    """Apply settings to Flask app.config for immediate effect."""
    if settings.ai_provider_format:
        config['AI_PROVIDER_FORMAT'] = settings.ai_provider_format
    if settings.api_key:
        config['api_key'] = settings.api_key
    if settings.api_base_url:
        config['api_base_url'] = settings.api_base_url
    if settings.text_model:
        config['TEXT_MODEL'] = settings.text_model
    if settings.image_model:
        config['IMAGE_MODEL'] = settings.image_model