"""
Template Custom Controller - Handle user-uploaded PPT templates
v0.6 Feature 3: Upload PPT, analyze style, generate custom template
"""
import os
import io
import json
import uuid
import base64
import logging
from datetime import datetime
from flask import Blueprint, request, send_file, current_app

from models import db
from models.user_template import UserTemplate

logger = logging.getLogger(__name__)

template_custom_bp = Blueprint('template_custom', __name__, url_prefix='/api/templates')


# === Storage helpers ===

def _get_custom_template_dir(template_id: str) -> str:
    """Get storage directory for a custom template."""
    storage_root = os.path.join(
        os.path.dirname(__file__), '..', 'template_custom'
    )
    template_dir = os.path.join(storage_root, template_id)
    os.makedirs(template_dir, exist_ok=True)
    return template_dir


def _get_thumbs_dir(template_id: str) -> str:
    """Get thumbnails directory."""
    thumbs_dir = os.path.join(_get_custom_template_dir(template_id), 'thumbs')
    os.makedirs(thumbs_dir, exist_ok=True)
    return thumbs_dir


# === Routes ===

@template_custom_bp.route('/custom', methods=['GET'])
def list_custom_templates():
    """GET /api/templates/custom - List all user-uploaded custom templates"""
    try:
        templates = UserTemplate.query.order_by(UserTemplate.created_at.desc()).all()
        return success_response({
            'templates': [t.to_dict() for t in templates]
        })
    except Exception as e:
        logger.error(f"[Template] List custom failed: {e}")
        return error_response(str(e), 500)


@template_custom_bp.route('/upload', methods=['POST'])
def upload_template():
    """
    POST /api/templates/upload
    Upload a PPTX file, analyze its design style, generate custom template.
    
    Form fields:
        - file: PPTX file (required)
        - name: Template display name (optional)
    """
    try:
        if 'file' not in request.files:
            return error_response('No file provided', 400)
        
        file = request.files['file']
        if not file.filename.endswith('.pptx'):
            return error_response('Only .pptx files are supported', 400)
        
        # Read file bytes
        pptx_bytes = file.read()
        file_size = len(pptx_bytes)
        
        # Check file size (50MB limit)
        if file_size > 50 * 1024 * 1024:
            return error_response('File size must be ≤ 50MB', 400)
        
        name = request.form.get('name', '') or ''
        
        # Create template record first
        template_id = str(uuid.uuid4())
        template = UserTemplate(
            id=template_id,
            name=name,
            file_path=f'uploads/{template_id}/template.pptx',  # placeholder
            file_size=file_size,
        )
        db.session.add(template)
        db.session.commit()
        
        # Save PPTX file
        template_dir = _get_custom_template_dir(template_id)
        pptx_path = os.path.join(template_dir, 'template.pptx')
        with open(pptx_path, 'wb') as f:
            f.write(pptx_bytes)
        
        # Update file_path
        template.file_path = pptx_path
        db.session.commit()
        
        # Analyze style in background (non-blocking)
        _analyze_template_async(template_id, pptx_path)
        
        return success_response({
            'template_id': template_id,
            'name': name or '自定义模板',
            'message': 'Upload successful, analyzing style...',
        })
        
    except Exception as e:
        logger.error(f"[Template] Upload failed: {e}")
        return error_response(str(e), 500)


def _analyze_template_async(template_id: str, pptx_path: str):
    """Analyze template design in background (fire and forget)."""
    try:
        from services.style_analyzer import StyleAnalyzer
        
        analyzer = StyleAnalyzer()
        result = analyzer.analyze_pptx(pptx_path, thumb_size=(400, 225))
        
        # Save thumbnails
        thumbs_dir = _get_thumbs_dir(template_id)
        thumbs_meta = {}
        
        for slide_idx, thumb_b64 in (result.get('slides_preview', {}) or {}).items():
            if thumb_b64:
                thumb_path = os.path.join(thumbs_dir, f'slide_{slide_idx}.png')
                with open(thumb_path, 'wb') as f:
                    f.write(base64.b64decode(thumb_b64))
                thumbs_meta[slide_idx] = f'/files/custom-templates/{template_id}/thumbs/slide_{slide_idx}.png'
        
        # Save design meta
        design_meta_path = os.path.join(_get_custom_template_dir(template_id), 'design_meta.json')
        with open(design_meta_path, 'w', encoding='utf-8') as f:
            json.dump({
                'primary_color': result.get('primary_color', '#003371'),
                'secondary_color': result.get('secondary_color', '#005691'),
                'font_title': result.get('font_title', 'Noto Sans SC'),
                'font_body': result.get('font_body', 'Noto Sans SC'),
                'layout_type': result.get('layout_type', '两栏'),
                'mood': result.get('mood', '专业'),
                'slide_count': result.get('slide_count', 0),
                'slides_preview': thumbs_meta,
                'analyzed_at': datetime.utcnow().isoformat(),
            }, f, ensure_ascii=False, indent=2)
        
        # Update template record
        template = UserTemplate.query.get(template_id)
        if template:
            first_thumb = thumbs_meta.get('0', '')
            template.name = template.name or result.get('mood', '自定义模板')
            if first_thumb:
                template.thumb_path = first_thumb
            db.session.commit()
        
        logger.info(f"[Template] Analysis complete for {template_id}")
        
    except Exception as e:
        logger.error(f"[Template] Analysis failed for {template_id}: {e}")


@template_custom_bp.route('/<template_id>', methods=['DELETE'])
def delete_custom_template(template_id):
    """DELETE /api/templates/<id> - Delete a custom template"""
    try:
        template = UserTemplate.query.get(template_id)
        if not template:
            return error_response('Template not found', 404)
        
        # Delete files
        template_dir = _get_custom_template_dir(template_id)
        import shutil
        if os.path.exists(template_dir):
            shutil.rmtree(template_dir)
        
        # Delete DB record
        db.session.delete(template)
        db.session.commit()
        
        return success_response({'deleted': template_id})
        
    except Exception as e:
        logger.error(f"[Template] Delete failed: {e}")
        return error_response(str(e), 500)


@template_custom_bp.route('/<template_id>/preview', methods=['GET'])
def get_template_preview(template_id):
    """GET /api/templates/<id>/preview - Get preview info"""
    try:
        template = UserTemplate.query.get(template_id)
        if not template:
            return error_response('Template not found', 404)
        
        # Read design meta
        design_meta_path = os.path.join(_get_custom_template_dir(template_id), 'design_meta.json')
        design_meta = {}
        if os.path.exists(design_meta_path):
            with open(design_meta_path, 'r', encoding='utf-8') as f:
                design_meta = json.load(f)
        
        return success_response({
            'template_id': template_id,
            'name': template.name or '自定义模板',
            'thumb_url': template.thumb_path,
            'file_size': template.file_size,
            'design_meta': design_meta,
        })
        
    except Exception as e:
        logger.error(f"[Template] Preview failed: {e}")
        return error_response(str(e), 500)


@template_custom_bp.route('/<template_id>/thumbs/<slide_idx>', methods=['GET'])
def get_slide_thumbnail(template_id, slide_idx):
    """GET /api/templates/<id>/thumbs/<idx> - Get a specific slide thumbnail"""
    try:
        thumb_path = os.path.join(_get_thumbs_dir(template_id), f'slide_{slide_idx}.png')
        if not os.path.exists(thumb_path):
            return error_response('Thumbnail not found', 404)
        return send_file(thumb_path, mimetype='image/png')
    except Exception as e:
        return error_response(str(e), 500)


# Helper responses
from flask import jsonify

def success_response(data):
    return jsonify({'success': True, **data})

def error_response(msg, code=400):
    return jsonify({'success': False, 'error': msg}), code