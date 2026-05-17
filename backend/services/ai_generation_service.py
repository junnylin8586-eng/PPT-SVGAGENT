#!/usr/bin/env python3
"""
AI Generation Service - 调用 MiniMax API 生成 PPT 页面内容（SVG）

Phase 3: 每个页面调用 AI 生成 SVG 内容
"""

import os
import re
import json
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# MiniMax API 配置
MINIMAX_API_KEY = os.environ.get('MINIMAX_API_KEY') or os.environ.get('MINIMAX_CN_API_KEY', '')
MINIMAX_BASE_URL = 'https://api.minimax.chat/v1'

# 项目上传目录
def get_projects_upload_dir():
    return os.path.join(os.environ.get('PROJECT_UPLOAD_DIR', 'D:\\AI\\ppt-agent\\uploads'), 'projects')


def load_ppt_master_prompts():
    """加载 ppt-master 的提示词模板"""
    prompts_dir = os.path.join(os.path.dirname(__file__), '..', 'ppt_master_engine', 'prompts')
    prompts = {}
    prompt_files = ['system_prompt.md', 'page_gen.md', 'svg_fix.md']
    for fname in prompt_files:
        fpath = os.path.join(prompts_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                prompts[fname] = f.read()
    return prompts


def build_page_generation_prompt(
    project_idea: str,
    page_outline: str,
    template_name: str = 'government_blue',
    page_index: int = 1,
    primary_color: str = '#003371',
    font_family: str = 'system-ui',
    layout_style: str = 'balanced',
    page_type: str = 'content',
    total_pages: int = 1,
    design_brief: str = '',
    enrichment_context: str = '',
) -> str:
    """
    构建页面生成提示词 — 增强版。

    整合了：智能内容优先级、页面类型感知、设计一致性约束、
    视觉质量要求、上下文补充。
    """
    accent_color = '#00875A'
    secondary_color = '#005691'

    # Layout density hint
    layout_note = {
        'compact': '内容紧凑，字号可略小，留白少',
        'balanced': '留白适中，内容与留白比例约 7:3',
        'spacious': '大量留白，字号偏大，内容居中或左对齐',
    }.get(layout_style, '留白适中')

    # Page type specific style guidance
    from services.page_content_planner import get_page_type_style_guidance
    type_guidance = get_page_type_style_guidance(page_type, template_name)

    # Enrichment context (AI-generated supplement when content is thin)
    enrichment_block = ''
    if enrichment_context:
        enrichment_block = f"""
## 内容补充参考（基于上下文的自动补充）
注意：以下是由AI基于本页上下文自动生成的内容补充建议，请将其与主要参考内容结合，
生成一页信息充分的幻灯片。不要完全照搬以下内容，而应将其作为扩展思路的参考。

{enrichment_context}
"""

    # Position context
    position_hint = ''
    if page_index == 1:
        position_hint = '（这是项目的第一页——封面页）'
    elif page_index == total_pages:
        position_hint = '（这是项目的最后一页——结束页）'
    elif page_index == 2:
        position_hint = '（这是目录页，紧跟封面之后）'

    prompt = f"""你是一个世界级的 PPT 幻灯片设计专家。请根据以下完整信息生成一页高质量的幻灯片 SVG 内容。

## 项目主题
{project_idea[:500]}

## 本页内容（主要参考）
{page_outline[:2000]}

{enrichment_block}
## 模板风格
{template_name}

## 页面信息
- 当前页码：第 {page_index} 页 / 共 {total_pages} 页{position_hint}
- 本页类型：{page_type}
- 布局风格：{layout_note}

## 样式参数
- 主色调：{primary_color}
- 强调色：{accent_color}
- 副色：{secondary_color}
- 字体：{font_family}（中文使用 Noto Sans SC 或 Microsoft YaHei）

{design_brief}

{type_guidance}

## SVG 技术规范（必须严格遵守）
1. viewBox="0 0 1280 720"，width="1280" height="720"
2. font-family="{font_family}, Noto Sans SC, Microsoft YaHei, sans-serif"
3. 主色调 {primary_color}，强调色 {accent_color}，副色 {secondary_color}
4. 禁止使用：foreignObject, animate*, script, mask, rgba(), @font-face
5. 使用 fill-opacity / stroke-opacity 代替 rgba()
6. 文字使用 <text> + <tspan> 实现换行，禁止使用 <foreignObject>
7. 所有文字必须在 viewBox 范围内，不得溢出
8. 只输出纯 SVG 代码，从 <svg> 标签开始，到 </svg> 标签结束
9. 不要输出 ```svg 或 ``` 标记，不要有任何解释文字
10. 确保 XML 格式完整正确，所有标签正确闭合

## 输出质量标准
- 信息密度适中，不要空洞（蓝底一行字）也不要过度拥挤
- 视觉层次分明：标题→核心内容→辅助信息→装饰元素
- 为不同类型的信息使用不同的视觉处理（如关键数据放大加色、列表用图标引导）
- 如果内容中有数据、步骤、对比等信息，使用适合的视觉化表达
"""
    return prompt


def call_minimax_llm(prompt: str, model: str = 'MiniMax-M2.7', fallback_outline: str = '') -> str:
    """
    直接调用 MiniMax Chat Completions API。
    使用 mmx-cli 作为 HTTP 代理调用。
    """
    import urllib.request
    import urllib.parse

    # 构建 API 请求
    request_data = {
        'model': 'MiniMax-M2.7',
        'messages': [
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 8192,
        'temperature': 0.7,
    }

    json_data = json.dumps(request_data).encode('utf-8')

    # 尝试使用 mmx-cli（如果可用）
    mmx_cli = os.environ.get('MMX_CLI_PATH', 'mmx-cli')
    if os.path.exists(mmx_cli.replace('mmx-cli', 'mmx-cli.exe')):
        mmx_cli = mmx_cli.replace('mmx-cli', 'mmx-cli.exe')

    # 先尝试直接调用 MiniMax API
    api_key = os.environ.get('MINIMAX_API_KEY') or os.environ.get('MINIMAX_CN_API_KEY', '')
    if not api_key:
        logger.warning('[AI Gen] No MINIMAX_API_KEY found, using fallback')
        return get_fallback_svg(fallback_outline)

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    req = urllib.request.Request(
        'https://api.minimax.chat/v1/chat/completions',
        data=json_data,
        headers=headers,
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f'[AI Gen] API call failed: {e}')
        return get_fallback_svg(fallback_outline)


def extract_svg_from_response(response: str) -> Optional[str]:
    """从 AI 响应中提取 SVG 代码
    
    使用多匹配策略：找到所有 <svg>...</svg> 配对后选最长的。
    避免 AI 描述文本中提及 </svg> 导致过早截断。
    """
    svg_pattern = re.compile(r'<svg[\s\S]*?</svg>', re.IGNORECASE)
    matches = list(svg_pattern.finditer(response))
    if not matches:
        return None
    # 选最长匹配 — AI 生成的完整 SVG 内容最长，描述性提及 </svg> 很短
    best = max(matches, key=lambda m: len(m.group(0)))
    svg = best.group(0)
    # 清理可能的 markdown 标记
    svg = re.sub(r'^```(?:svg)?\s*', '', svg, flags=re.IGNORECASE).strip()
    svg = re.sub(r'\s*```$', '', svg).strip()
    return svg


def get_fallback_svg(outline_content: str, page_index: int = 1) -> str:
    """当 AI 不可用时的 fallback SVG（简单占位）"""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#003371"/>
  <text x="640" y="320" font-family="system-ui, sans-serif" font-size="52"
        fill="white" text-anchor="middle" font-weight="bold">第 {page_index} 页</text>
  <text x="640" y="400" font-family="system-ui, sans-serif" font-size="24"
        fill="#AACCEE" text-anchor="middle">{outline_content[:60]}</text>
  <rect x="560" y="440" width="160" height="6" rx="3" fill="#00875A"/>
</svg>'''


def generate_page_svg(
    project_idea: str,
    outline_content: str = '',
    page_instruction: str = '',
    template_name: str = 'government_blue',
    page_index: int = 1,
    output_dir: Optional[str] = None,
    primary_color: str = '#003371',
    font_family: str = 'system-ui',
    layout_style: str = 'balanced',
    total_pages: int = 1,
    design_brief: str = '',
    neighbor_summaries: Optional[List[str]] = None,
) -> Dict[str, str]:
    """
    生成单页 SVG 内容 — 增强版。

    自动判断内容优先级：比较 outline_content 和 page_instruction 的详细程度，
    以更详细的作为主要参考内容，另一份作为辅助参考。
    当两者内容都较简短时，利用上下文自动补充。

    Args:
        project_idea: 项目主题描述
        outline_content: 本页大纲
        page_instruction: 本页详细描述
        total_pages: 项目总页数
        design_brief: 项目统一设计规范
        neighbor_summaries: 相邻页面摘要（用于上下文补充）
    Returns:
        {'svg_content': str, 'svg_path': str}
    """
    from services.page_content_planner import plan_page_content, build_unified_design_brief

    # Step 1: Smart content planning — determine primary vs auxiliary
    plan = plan_page_content(
        outline_content=outline_content,
        description_content=page_instruction,
        page_index=page_index - 1,  # 0-based for planner
        total_pages=total_pages,
        project_idea=project_idea,
        neighbor_summaries=neighbor_summaries,
    )

    effective_outline = plan['primary_content']
    if plan['auxiliary_content']:
        effective_outline = (
            f"【主要参考内容】\n{plan['primary_content']}\n\n"
            f"【辅助参考内容】\n{plan['auxiliary_content']}"
        )

    # Step 2: Unified design brief (cached per project, but computed here)
    if not design_brief:
        design_brief = build_unified_design_brief(
            project_idea=project_idea,
            template_name=template_name,
            primary_color=primary_color,
        )

    # Step 3: Enrichment context (AI supplement when content is thin)
    enrichment = plan['enrichment_context'] if plan['needs_enrichment'] else ''

    # Step 4: Build enhanced prompt
    prompt = build_page_generation_prompt(
        project_idea=project_idea,
        page_outline=effective_outline,
        template_name=template_name,
        page_index=page_index,
        primary_color=primary_color,
        font_family=font_family,
        layout_style=layout_style,
        page_type=plan['page_type'],
        total_pages=total_pages,
        design_brief=design_brief,
        enrichment_context=enrichment,
    )

    logger.info(
        f'[AI Gen] Page {page_index}/{total_pages} type={plan["page_type"]} '
        f'detail={plan["detail_level"]} enrich={plan["needs_enrichment"]} '
        f'primary={plan["primary_source"]}'
    )

    response = call_minimax_llm(prompt, fallback_outline=effective_outline)
    svg_content = extract_svg_from_response(response)

    if not svg_content:
        logger.warning(f'[AI Gen] No SVG extracted for page {page_index}, using fallback')
        svg_content = get_fallback_svg(outline_content, page_index)

    # Save to file
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        svg_path = os.path.join(output_dir, f'slide_{page_index:02d}.svg')
        with open(svg_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        logger.info(f'[AI Gen] Saved SVG: {svg_path}')
        return {'svg_content': svg_content, 'svg_path': svg_path}

    return {'svg_content': svg_content, 'svg_path': ''}


def save_svg_for_page(project_id: str, page_index: int, svg_content: str) -> str:
    """保存项目页面的 SVG 文件，返回访问路径（相对路径）"""
    project_dir = os.path.join(get_projects_upload_dir(), project_id)
    os.makedirs(project_dir, exist_ok=True)
    svg_path = os.path.join(project_dir, f'slide_{page_index:02d}.svg')
    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    # 返回相对路径（相对于 uploads/projects/）
    # Use forward slash for URL compatibility (os.path.normpath handles fs access)
    return f'{project_id}/slide_{page_index:02d}.svg'