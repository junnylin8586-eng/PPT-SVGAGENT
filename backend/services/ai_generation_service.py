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
) -> str:
    """
    构建页面生成提示词。
    实际使用时从 ppt-master 的 prompts 加载结构化提示词模板。
    """
    template_svg_dir = os.path.join(
        os.path.dirname(__file__), '..', 'ppt_master_engine',
        'templates', 'layouts', template_name
    )

    # 派生颜色
    import re
    def hex_to_rgb(hex_color: str) -> str:
        h = hex_color.lstrip('#')
        if len(h) == 6:
            r, g, b = h[:2], h[2:4], h[4:6]
            return f'#{int(r,16):02X}{int(g,16):02X}{int(b,16):02X}'
        return hex_color
    
    # 计算强调色（略微调暗/调亮主色）
    accent_color = '#00875A'  # 默认绿
    
    # 布局密度
    layout_note = {
        'compact': '内容紧凑，字号可略小，留白少',
        'balanced': '留白适中，内容与留白比例约 7:3',
        'spacious': '大量留白，字号偏大，内容居中或左对齐',
    }.get(layout_style, '留白适中')

    prompt = f"""你是一个专业的 PPT 幻灯片设计师。请根据以下信息生成一页幻灯片的 SVG 内容。

## 项目主题
{project_idea}

## 本页大纲
{page_outline}

## 模板风格
{template_name}

## 样式要求
- 主色调：{primary_color}
- 字体：{font_family}（如需中文字体请使用 Noto Sans SC 或 PingFang SC）
- 布局风格：{layout_note}

## SVG 输出要求
1. 输出完整的 SVG 文件内容，使用 viewBox="0 0 1280 720"
2. 使用 font-family="{font_family}, Noto Sans SC, sans-serif"（英文+中文字体组合）
3. 主色调使用 {primary_color}，强调色使用 {accent_color}，副色使用 #005691
4. 不要使用无效的 SVG 属性（如 font-family 的中文名）
5. 确保所有文字在 viewBox 范围内不溢出
6. 只输出 SVG 代码，不要有 ```svg 标记，用纯粹的 <svg> 标签开始
7. 背景用浅色（白色或 #F5F7FA），不要用深色背景

## 页面序号
第 {page_index} 页
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
        with urllib.request.urlopen(req, timeout=120) as resp:
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
) -> Dict[str, str]:
    """
    生成单页 SVG 内容。

    Args:
        project_idea: 项目主题描述
        outline_content: 页面标题（简短）
        page_instruction: 页面完整提示词（核心主题+内容+布局+风格）
                          优先级高于 outline_content
    Returns:
        {'svg_content': str, 'svg_path': str}
    """
    # 两者结合：outline_content 是用户指定的大纲（主要依据），
    # description_content 是详细描述（辅助参考）
    effective_outline = outline_content
    if page_instruction:
        effective_outline = f"{outline_content}\n\n补充参考：{page_instruction}"
    prompt = build_page_generation_prompt(
        project_idea=project_idea,
        page_outline=effective_outline,
        template_name=template_name,
        page_index=page_index,
        primary_color=primary_color,
        font_family=font_family,
        layout_style=layout_style,
    )

    response = call_minimax_llm(prompt, fallback_outline=effective_outline)
    svg_content = extract_svg_from_response(response)

    if not svg_content:
        logger.warning(f'[AI Gen] No SVG extracted for page {page_index}, using fallback')
        svg_content = get_fallback_svg(outline_content, page_index)

    # 保存到文件
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
    return f'{project_id}/slide_{page_index:02d}.svg'