"""
PPT Controller - Core REST API for PPT Agent
Phase 3: Generation + SVG + Export
"""
import logging
import os
import uuid
import json
import re
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, send_from_directory, Response
from werkzeug.utils import secure_filename
from pathlib import Path
from services.theme_analysis_service import analyze_theme_stream, analyze_theme_sync
import logging

logger = logging.getLogger(__name__)

from models import db
from models.project import Project
from models.page import Page
from services.ai_generation_service import generate_page_svg, save_svg_for_page, get_fallback_svg
from services.svg_export_service import create_pptx_from_svgs

logger = logging.getLogger(__name__)

ppt_bp = Blueprint('ppt', __name__, url_prefix='/api/ppt')

# ============================================================================
# Utils
# ============================================================================

def success_response(data=None, status_code=200):
    resp = {'success': True}
    if data is not None:
        resp['data'] = data
    return jsonify(resp), status_code


def error_response(message, status_code=400):
    return jsonify({'success': False, 'error': message}), status_code


def not_found(resource='Resource'):
    return jsonify({'success': False, 'error': f'{resource} not found'}), 404


def get_upload_dir():
    return current_app.config.get('UPLOAD_FOLDER',
                                  os.path.join(os.path.dirname(__file__), '..', '..', 'uploads'))


# ============================================================================
# Projects
# ============================================================================

@ppt_bp.route('/projects', methods=['POST'])
def create_project():
    """POST /api/ppt/projects - Create new PPT project"""
    try:
        data = request.get_json() or {}

        project = Project(
            id=str(uuid.uuid4())[:8],
            name=data.get('name', '未命名项目'),
            idea_prompt=data.get('idea_prompt', ''),
            outline_text=data.get('outline_text', ''),
            description_text=data.get('description_text', ''),
            extra_requirements=data.get('extra_requirements'),
            template_path=data.get('template_path'),
            image_aspect_ratio=data.get('image_aspect_ratio', '16:9'),
            generation_mode=data.get('generation_mode', 'guide'),
            status='DRAFT',
        )
        db.session.add(project)
        db.session.commit()

        logger.info(f"[PPT] Created project {project.id}: {project.name}")
        return success_response(project.to_dict(), 201)

    except Exception as e:
        db.session.rollback()
        logger.error(f"[PPT] Failed to create project: {e}")
        return error_response(str(e), 500)


@ppt_bp.route('/projects', methods=['GET'])
def list_projects():
    """GET /api/ppt/projects - List all non-deleted projects"""
    try:
        projects = Project.query.filter_by(is_deleted=False).order_by(Project.updated_at.desc()).all()
        return success_response([p.to_dict() for p in projects])
    except Exception as e:
        logger.error(f"[PPT] Failed to list projects: {e}")
        return error_response(str(e), 500)


@ppt_bp.route('/projects/<project_id>', methods=['GET'])
def get_project(project_id):
    """GET /api/ppt/projects/<id>"""
    project = Project.query.filter_by(id=project_id, is_deleted=False).first()
    if not project:
        return not_found('Project')
    return success_response(project.to_dict(include_pages=True))


@ppt_bp.route('/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    """PUT /api/ppt/projects/<id>"""
    project = Project.query.filter_by(id=project_id, is_deleted=False).first()
    if not project:
        return not_found('Project')

    try:
        data = request.get_json() or {}
        for field in ['name', 'idea_prompt', 'outline_text', 'description_text',
                      'extra_requirements', 'template_path', 'image_aspect_ratio',
                      'generation_mode', 'status',
                      'primary_color', 'font_family', 'layout_style']:
            if field in data:
                setattr(project, field, data[field])
        project.updated_at = datetime.utcnow()
        from utils.db_retry import retry_on_lock
        retry_on_lock(db.session.commit)()
        return success_response(project.to_dict())
    except Exception as e:
        db.session.rollback()
        logger.error(f"[PPT] Failed to update project {project_id}: {e}")
        return error_response(str(e), 500)


@ppt_bp.route('/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    """DELETE /api/ppt/projects/<id>"""
    project = Project.query.filter_by(id=project_id, is_deleted=False).first()
    if not project:
        return not_found('Project')
    try:
        project.is_deleted = True
        project.updated_at = datetime.utcnow()
        db.session.commit()
        return success_response({'deleted': project_id})
    except Exception as e:
        db.session.rollback()
        logger.error(f"[PPT] Failed to delete project {project_id}: {e}")
        return error_response(str(e), 500)


# ============================================================================
# Pages
# ============================================================================

@ppt_bp.route('/projects/<project_id>/pages', methods=['GET'])
def list_pages(project_id):
    """GET /api/ppt/projects/<id>/pages - List all pages with SVG"""
    project = Project.query.filter_by(id=project_id, is_deleted=False).first()
    if not project:
        return not_found('Project')
    try:
        pages = Page.query.filter_by(project_id=project_id, is_deleted=False).order_by(Page.order_index).all()
        return success_response([p.to_dict() for p in pages])
    except Exception as e:
        logger.error(f"[PPT] Failed to list pages: {e}")
        return error_response(str(e), 500)


@ppt_bp.route('/projects/<project_id>/pages', methods=['POST'])
def create_pages_batch(project_id):
    """POST /api/ppt/projects/<id>/pages - Create or update pages from outline"""
    project = Project.query.filter_by(id=project_id, is_deleted=False).first()
    if not project:
        return not_found('Project')

    try:
        data = request.get_json() or {}
        outlines = data.get('outlines', [])  # [{order_index, outline_content, part}]
        created = []

        for item in outlines:
            existing = Page.query.filter_by(
                project_id=project_id,
                order_index=item['order_index'],
                is_deleted=False
            ).first()

            if existing:
                existing.set_outline_content(item.get('outline_content', ''))
                if item.get('part'):
                    existing.part = item['part']
                # Store per-page generation instruction (full body text)
                if item.get('page_instruction'):
                    existing.set_description_content(item['page_instruction'])
                # Reset to PENDING so trigger_generation can find and regenerate this page
                existing.status = 'PENDING'
                existing.svg_path = None  # Clear old SVG
                created.append(existing)
            else:
                has_instruction = bool(item.get('page_instruction'))
                page = Page(
                    project_id=project_id,
                    order_index=item['order_index'],
                    part=item.get('part', ''),
                    status='DESCRIPTION_GENERATED' if has_instruction else 'PENDING',
                )
                # Use setters so JSON encoding is consistent (setter does json.dumps)
                page.set_outline_content(item.get('outline_content', ''))
                page.set_description_content(item.get('page_instruction', ''))
                db.session.add(page)
                created.append(page)

        project.updated_at = datetime.utcnow()
        project.status = 'GENERATING'
        from utils.db_retry import retry_on_lock
        retry_on_lock(db.session.commit)()
        return success_response({'pages': [p.to_dict() for p in created]}, 201)

    except Exception as e:
        db.session.rollback()
        logger.error(f"[PPT] Failed to create pages: {e}")
        return error_response(str(e), 500)


@ppt_bp.route('/projects/<project_id>/pages/<page_id>', methods=['PUT'])
def update_page(project_id, page_id):
    """PUT /api/ppt/projects/<id>/pages/<page_id>"""
    page = Page.query.filter_by(id=page_id, project_id=project_id, is_deleted=False).first()
    if not page:
        return not_found('Page')

    try:
        data = request.get_json() or {}
        if 'outline_content' in data:
            page.set_outline_content(data['outline_content'])
            page.status = 'PENDING'  # Reset for regeneration
        if 'description_content' in data:
            page.set_description_content(data['description_content'])
        if 'part' in data:
            page.part = data['part']
        if 'status' in data:
            page.status = data['status']
        if 'svg_path' in data:
            page.svg_path = data['svg_path']
        if 'svg_content' in data:
            # 保存 SVG 内容到文件
            svg_rel_path = save_svg_for_page(project_id, page.order_index, data['svg_content'])
            page.svg_path = svg_rel_path

        db.session.commit()
        return success_response(page.to_dict())

    except Exception as e:
        db.session.rollback()
        logger.error(f"[PPT] Failed to update page {page_id}: {e}")
        return error_response(str(e), 500)


@ppt_bp.route('/projects/<project_id>/pages/<page_id>', methods=['DELETE'])
def delete_page(project_id, page_id):
    """DELETE /api/ppt/projects/<id>/pages/<page_id>"""
    page = Page.query.filter_by(id=page_id, project_id=project_id, is_deleted=False).first()
    if not page:
        return not_found('Page')
    try:
        page.is_deleted = True
        db.session.commit()
        return success_response({'deleted': page_id})
    except Exception as e:
        db.session.rollback()
        logger.error(f"[PPT] Failed to delete page {page_id}: {e}")
        return error_response(str(e), 500)


@ppt_bp.route('/projects/<project_id>/pages/<page_id>/svg', methods=['GET'])
def get_page_svg(project_id, page_id):
    """GET /api/ppt/projects/<id>/pages/<page_id>/svg"""
    page = Page.query.filter_by(id=page_id, project_id=project_id, is_deleted=False).first()
    if not page:
        return not_found('Page')

    svg_path = page.get_svg_path()
    if not svg_path or not os.path.exists(svg_path):
        return error_response('SVG not generated yet', 404)

    with open(svg_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return success_response({'svg_content': content})


# ============================================================================
# Generate (Phase 3: AI → SVG)
# ============================================================================

@ppt_bp.route('/projects/<project_id>/generate', methods=['POST'])
def trigger_generation(project_id):
    """
    POST /api/ppt/projects/<id>/generate
    触发 AI 生成：为每个 PENDING 页面生成 SVG
    """
    project = Project.query.filter_by(id=project_id, is_deleted=False).first()
    if not project:
        return not_found('Project')

    try:
        data = request.get_json() or {}
        template_name = data.get('template', project.template_path or 'government_blue')

        # Get ALL non-deleted pages (not just PENDING) — regenerate everything
        pages = Page.query.filter_by(
            project_id=project_id, is_deleted=False
        ).order_by(Page.order_index).all()

        if not pages:
            return error_response('No pages to generate. Create pages first.')

        # Reset ALL pages to PENDING before generation so polling can track progress
        for p in pages:
            p.status = 'PENDING'
            p.svg_path = None  # Clear stale SVG path
        db.session.commit()

        task_id = f"ppt_gen_{uuid.uuid4().hex[:8]}"
        logger.info(f"[PPT] Task {task_id}: Generating {len(pages)} pages with template={template_name}")

        # Auto-fill empty outlines from idea_prompt
        project_idea = (project.idea_prompt or project.outline_text or project.description_text or '')
        logger.info(f'[PPT] Task {task_id}: project_idea length={len(project_idea)}, pages={len(pages)}')
        logger.info(f'[PPT] Task {task_id}: idea preview: {project_idea[:100]}')
        if project_idea and len(project_idea) > 20:
            try:
                from services.outline_generator import generate_outlines_from_idea
                auto_outlines = generate_outlines_from_idea(project_idea)
                logger.info(f'[PPT] Task {task_id}: auto_outlines count={len(auto_outlines)}')
                for page in pages:
                    oc = page.outline_content or ''
                    logger.info(f'[PPT] Task {task_id}: page {page.order_index} current outline={repr(oc[:50]) if oc else "(empty)"}')
                    if not oc or str(oc).strip() == '' or oc == 'null':
                        idx = page.order_index
                        if idx < len(auto_outlines):
                            new_oc = auto_outlines[idx].get('outline_content', '')
                            new_part = auto_outlines[idx].get('part', '')
                            page.set_outline_content(new_oc)
                            if new_part:
                                page.part = new_part
                            logger.info(f'[PPT] Task {task_id}: page {page.order_index} auto-filled: oc={repr(new_oc[:30])}, part={new_part}')
                    else:
                        logger.info(f'[PPT] Task {task_id}: page {page.order_index} outline already set, skipping')
            except Exception as e:
                logger.warning(f'[PPT] Task {task_id}: Auto outline failed: {e}', exc_info=True)

        # Commit outline changes BEFORE generation (SVG can take a long time)
        from utils.db_retry import retry_on_lock
        retry_on_lock(db.session.commit)()
        logger.info(f'[PPT] Task {task_id}: Outline auto-fill committed, starting SVG generation...')
        project_idea = (project.idea_prompt or project.outline_text or project.description_text or '')
        primary_color = project.primary_color or '#003371'
        font_family = project.font_family or 'system-ui'
        layout_style = project.layout_style or 'balanced'
        results = []
        upload_dir = get_upload_dir()
        project_svg_dir = os.path.join(upload_dir, 'projects', project_id)
        os.makedirs(project_svg_dir, exist_ok=True)

        for page in pages:
            page_idea = page.get_outline_content() or ''
            page_instruction = page.get_description_content() or ''
            # Skip pages with truly empty outlines (defense against SSE parsing bugs)
            if not page_idea or not page_idea.strip():
                logger.warning(f'[PPT] Task {task_id}: Skipping page {page.order_index} - empty outline')
                page.status = 'SKIPPED'
                continue
            try:
                result = generate_page_svg(
                    project_idea=project_idea,
                    outline_content=page_idea,
                    page_instruction=page_instruction,
                    template_name=template_name,
                    page_index=page.order_index + 1,
                    output_dir=project_svg_dir,
                    primary_color=primary_color,
                    font_family=font_family,
                    layout_style=layout_style,
                )
                # 保存相对路径
                svg_filename = os.path.basename(result['svg_path'])
                svg_rel_path = f'{project_id}/{svg_filename}'
                page.svg_path = svg_rel_path
                page.status = 'GENERATED'
                results.append({'page_id': page.id, 'svg_path': svg_rel_path, 'page_index': page.order_index})
                # Commit after each page so polling sees progress
                try:
                    db.session.commit()
                except Exception:
                    pass
            except Exception as gen_err:
                logger.error(f'[PPT] Task {task_id}: Page {page.order_index} generation failed: {gen_err}', exc_info=True)
                page.status = 'FAILED'
                # Commit individual page status so polling can see progress
                try:
                    db.session.commit()
                except Exception:
                    pass

        project.status = 'COMPLETED'
        project.updated_at = datetime.utcnow()
        retry_on_lock(db.session.commit)()

        return success_response({
            'task_id': task_id,
            'pages': results,
            'template': template_name,
            'status': 'completed',
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"[PPT] Generation failed: {e}")
        return error_response(str(e), 500)


@ppt_bp.route('/projects/<project_id>/pages/<page_id>/generate', methods=['POST'])
def regenerate_single_page(project_id, page_id):
    """
    POST /api/ppt/projects/<id>/pages/<page_id>/generate
    为指定页面重新生成 SVG（单页）
    """
    project = Project.query.filter_by(id=project_id, is_deleted=False).first()
    if not project:
        return not_found('Project')
    page = Page.query.filter_by(id=page_id, project_id=project_id, is_deleted=False).first()
    if not page:
        return not_found('Page')

    try:
        data = request.get_json() or {}
        template_name = data.get('template', project.template_path or 'government_blue')
        primary_color = project.primary_color or '#003371'
        font_family = project.font_family or 'system-ui'
        layout_style = project.layout_style or 'balanced'
        project_idea = (project.idea_prompt or project.outline_text or project.description_text or '')

        upload_dir = get_upload_dir()
        project_svg_dir = os.path.join(upload_dir, 'projects', project_id)
        os.makedirs(project_svg_dir, exist_ok=True)

        page_idea = page.get_outline_content() or ''
        page_instruction = page.get_description_content() or ''
        logger.info(f'[PPT] Regenerate page {page.order_index} with outline={repr(page_idea[:50]) if page_idea else None}')

        result = generate_page_svg(
            project_idea=project_idea,
            outline_content=page_idea,
            page_instruction=page_instruction,
            template_name=template_name,
            page_index=page.order_index + 1,
            output_dir=project_svg_dir,
            primary_color=primary_color,
            font_family=font_family,
            layout_style=layout_style,
        )

        svg_filename = os.path.basename(result['svg_path'])
        svg_rel_path = f'{project_id}/{svg_filename}'
        page.svg_path = svg_rel_path
        page.status = 'GENERATED'
        project.status = 'COMPLETED'
        project.updated_at = datetime.utcnow()
        from utils.db_retry import retry_on_lock
        retry_on_lock(db.session.commit)()

        return success_response({'page': page.to_dict(), 'svg_path': svg_rel_path})

    except Exception as e:
        db.session.rollback()
        logger.error(f'[PPT] Single page generation failed: {e}')
        return error_response(str(e), 500)


# ============================================================================
# Export (Phase 3: SVG → PPTX)
# ============================================================================

@ppt_bp.route('/projects/<project_id>/export', methods=['POST'])
def export_pptx(project_id):
    """POST /api/ppt/projects/<id>/export - SVG → PPTX via Path D"""
    project = Project.query.filter_by(id=project_id, is_deleted=False).first()
    if not project:
        return not_found('Project')

    try:
        data = request.get_json() or {}
        page_ids = data.get('page_ids')  # optional filter

        # 获取所有 GENERATED 页面
        query = Page.query.filter_by(
            project_id=project_id, is_deleted=False
        ).filter(Page.status.in_(['GENERATED', 'DESCRIPTION_GENERATED']))

        if page_ids:
            query = query.filter(Page.id.in_(page_ids))

        pages = query.order_by(Page.order_index).all()
        if not pages:
            return error_response('No generated pages to export')

        # 收集 SVG 文件路径
        upload_dir = get_upload_dir()
        svg_files = []
        for page in pages:
            rel_path = page.get_svg_path()  # 相对路径: project_id/slide_XX.svg
            if rel_path:
                svg_abs = os.path.join(upload_dir, 'projects', rel_path)
                if os.path.exists(svg_abs):
                    svg_files.append(Path(svg_abs))  # Path 对象，svg_export_service 需要
                else:
                    logger.warning(f'[PPT] SVG not found: {svg_abs}')

        if not svg_files:
            return error_response('No SVG files found')

        # 输出 PPTX 到项目目录
        export_dir = os.path.join(upload_dir, 'exports', project_id)
        os.makedirs(export_dir, exist_ok=True)
        output_path = os.path.join(export_dir, f'{project.name or project_id}.pptx')

        success = create_pptx_from_svgs(
            svg_files=svg_files,
            output_path=output_path,
            canvas_format='ppt169',
            use_native_shapes=True,
            transition='fade',
        )

        if success:
            rel_path = f'exports/{project_id}/{os.path.basename(output_path)}'
            return success_response({
                'pptx_path': rel_path,
                'size_kb': os.path.getsize(output_path) // 1024,
                'page_count': len(svg_files),
            })
        else:
            return error_response('PPTX creation failed', 500)

    except Exception as e:
        logger.error(f"[PPT] Export failed: {e}")
        return error_response(str(e), 500)


# ============================================================================
# Files (SVG 访问)
# ============================================================================

@ppt_bp.route('/files/<path:filename>', methods=['GET'])
def serve_file(filename):
    """GET /api/ppt/files/<path> - 访问 SVG/PPTX 文件"""
    from flask import make_response, request as flask_request
    upload_dir = get_upload_dir()
    is_download = flask_request.args.get('download') == '1'

    # SVG 文件: uploads/projects/{project_id}/...   filename格式: {project_id}/slide_XX.svg
    # 导出文件: uploads/exports/{project_id}/...   filename格式: exports/{project_id}/filename.pptx

    # 先按原格式查找
    # SVG: uploads/projects/{filename}
    svg_full = os.path.abspath(os.path.join(upload_dir, 'projects', filename))
    if svg_full.startswith(os.path.abspath(upload_dir)) and os.path.exists(svg_full):
        resp = send_from_directory(os.path.join(upload_dir, 'projects'), filename)
        if is_download:
            resp.headers['Content-Disposition'] = f'attachment; filename="{os.path.basename(filename)}"'
        return resp

    # 导出: uploads/exports/{project_id}/filename.pptx
    if filename.startswith('exports/'):
        subpath = filename[len('exports/'):]  # {project_id}/filename.pptx
        exp_dir = os.path.dirname(subpath)  # {project_id}
        exp_file = os.path.basename(subpath)  # filename.pptx
        exp_full = os.path.abspath(os.path.join(upload_dir, 'exports', exp_dir, exp_file))
        if exp_full.startswith(os.path.abspath(upload_dir)) and os.path.exists(exp_full):
            resp = send_from_directory(os.path.join(upload_dir, 'exports', exp_dir), exp_file)
            # For downloads, set Content-Disposition so browser triggers save dialog
            if is_download:
                from urllib.parse import quote
                ascii_name = exp_file.encode('ascii', 'ignore').decode() or exp_file
                resp.headers['Content-Disposition'] = f'attachment; filename="{ascii_name}"'
                resp.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
            return resp

    return not_found('File')


# ============================================================================
# Templates
# ============================================================================

@ppt_bp.route('/templates/layouts', methods=['GET'])
def list_builtin_templates():
    """GET /api/ppt/templates/layouts - 17 built-in templates"""
    try:
        engine_path = os.path.join(
            os.path.dirname(__file__), '..', 'ppt_master_engine',
            'templates', 'layouts'
        )
        index_file = os.path.join(engine_path, 'layouts_index.json')

        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            # 转换格式：{id, name, summary, keywords}
            templates = []
            for tid, info in raw.items():
                name = info.get('name') or info.get('summary', tid)
                if isinstance(info, dict):
                    templates.append({
                        'layout_id': tid,
                        'name': name if name != tid else tid,
                        'category': _categorize_template(tid),
                        'summary': info.get('summary', ''),
                        'keywords': info.get('keywords', []),
                    })
                else:
                    templates.append({'layout_id': tid, 'name': tid, 'category': 'other'})
            return success_response({'templates': templates})

        return success_response({'templates': []})

    except Exception as e:
        logger.error(f"[PPT] Template list failed: {e}")
        return error_response(str(e), 500)


def _categorize_template(tid: str) -> str:
    """根据模板 ID 推断分类"""
    if any(k in tid for k in ['government', 'china', '中']):
        return '政府央企'
    elif any(k in tid for k in ['学术', 'academic', 'university', '大学']):
        return '学术教育'
    elif any(k in tid for k in ['bank', '金融', '招商']):
        return '金融银行'
    elif any(k in tid for k in ['medical', '医疗']):
        return '医疗健康'
    elif any(k in tid for k in ['ai', 'ai_ops', 'anthropic', 'tech']):
        return '科技AI'
    return '通用商务'


@ppt_bp.route('/templates/thumbnail/<template_id>/<slide_name>', methods=['GET'])
def get_template_thumbnail(template_id, slide_name):
    """GET /api/ppt/templates/thumbnail/<id>/<slide> - 获取模板缩略图"""
    engine_path = os.path.join(
        os.path.dirname(__file__), '..', 'ppt_master_engine',
        'templates', 'layouts', template_id, slide_name
    )
    if not os.path.exists(engine_path):
        return not_found('Template slide')

    from services.svg_render_service import render_svg_file_to_png
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        render_svg_file_to_png(engine_path, tmp_path, viewport_width=400, scale=1)
        return send_from_directory(os.path.dirname(tmp_path), os.path.basename(tmp_path))
    except Exception as e:
        return error_response(str(e), 500)


@ppt_bp.route('/analyze-theme', methods=['POST'])
def analyze_theme():
    """
    POST /api/ppt/analyze-theme
    AI分析主题描述 → 生成结构化大纲
    HTTP trigger + SSE streaming

    Body: { "theme_text": "..." }
    Returns: text/event-stream with progress events
    """
    data = request.get_json() or {}
    theme_text = (data.get('theme_text') or data.get('idea_prompt') or '').strip()


    if not theme_text:
        return error_response('theme_text is required', 400)

    # Resolve provider HERE (inside request context) - avoids app context issues
    from services.ai_providers import get_text_provider
    text_provider = get_text_provider()

    def generate():
        """SSE generator - yields all analyze_theme_stream events"""
        for event in analyze_theme_stream(theme_text, text_provider=text_provider):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        }
    )



@ppt_bp.route('/templates/upload', methods=['POST'])
def upload_template():
    """"POST /api/ppt/templates/upload - PPTX custom template (Phase 4)"""
    return success_response({'message': 'Phase 4 feature'})
    """POST /api/ppt/templates/upload - PPTX → custom template (Phase 4)"""
    return success_response({'message': 'Phase 4 feature'})