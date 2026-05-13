#!/usr/bin/env python3
"""
SVG Render Service - 使用 Playwright 将 SVG 渲染为 PNG/预览

提供两种模式：
1. render_svg_file_to_png(svg_path, png_path) - 渲染本地 SVG 文件
2. render_svg_string_to_png(svg_content, png_path) - 渲染 SVG 字符串

依赖安装：
    uv pip install playwright
    playwright install chromium
"""

import os
import logging
import tempfile
import base64
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Playwright 浏览器路径
_PW_BROWSERS = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ms-playwright')
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = _PW_BROWSERS

_browser = None
_playwright = None


def _ensure_playwright():
    global _playwright
    if _playwright is None:
        from playwright.sync_api import sync_playwright
        _playwright = sync_playwright().start()
        logger.info('[SVGRender] Playwright started')
    return _playwright


def _get_browser():
    global _browser, _playwright
    if _browser is None:
        pw = _ensure_playwright()
        chromium_exe = os.path.join(
            _PW_BROWSERS, 'chromium-1208', 'chrome-win64', 'chrome.exe'
        )
        if os.path.exists(chromium_exe):
            _browser = pw.chromium.launch(
                headless=True,
                executable_path=chromium_exe,
                args=['--disable-dev-shm-usage', '--no-sandbox', '--disable-setuid-sandbox'],
            )
        else:
            _browser = pw.chromium.launch(headless=True)
        logger.info('[SVGRender] Browser launched')
    return _browser


def render_svg_string_to_png(
    svg_content: str,
    output_path: str,
    viewport_width: int = 1280,
    viewport_height: int = 720,
    scale: float = 1.0,
    bg_color: Optional[str] = None,
) -> str:
    """
    将 SVG 字符串渲染为 PNG 文件。

    Args:
        svg_content: SVG 内容的字符串
        output_path: 输出的 PNG 文件路径
        viewport_width: 视口宽度（默认 1280）
        viewport_height: 视口高度（默认 720）
        scale: 渲染缩放比例（默认 1.0）
        bg_color: 背景色（可选，默认透明）

    Returns:
        输出 PNG 文件的路径
    """
    browser = _get_browser()
    page = browser.new_page(
        viewport={'width': viewport_width, 'height': viewport_height},
        device_scale_factor=scale,
    )

    try:
        # 设置背景色
        if bg_color:
            page.set_extra_http_headers({'--bg-color': bg_color})
            html_content = f'''
            <!DOCTYPE html>
            <html>
            <head><style>
            body {{ margin: 0; background: {bg_color}; display: flex; align-items: center; justify-content: center; height: 100vh; }}
            svg {{ max-width: 100%; max-height: 100vh; }}
            </style></head>
            <body>{svg_content}</body>
            </html>'''
        else:
            html_content = f'''
            <!DOCTYPE html>
            <html>
            <head><style>
            body {{ margin: 0; display: flex; align-items: center; justify-content: center; height: 100vh; background: transparent; }}
            svg {{ max-width: 100%; max-height: 100vh; }}
            </style></head>
            <body>{svg_content}</body>
            </html>'''

        page.set_content(html_content, wait_until='networkidle')
        page.wait_for_timeout(500)  # 等待字体渲染

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        page.screenshot(path=output_path, type='png')
        logger.info(f'[SVGRender] Saved PNG: {output_path}')
        return output_path

    finally:
        page.close()


def render_svg_file_to_png(
    svg_path: str,
    output_path: str,
    viewport_width: int = 1280,
    viewport_height: int = 720,
    scale: float = 1.0,
    bg_color: Optional[str] = None,
) -> str:
    """将本地 SVG 文件渲染为 PNG。"""
    with open(svg_path, 'r', encoding='utf-8') as f:
        svg_content = f.read()
    return render_svg_string_to_png(svg_content, output_path, viewport_width, viewport_height, scale, bg_color)


def svg_to_data_url(svg_content: str) -> str:
    """将 SVG 字符串转换为 data: URL（用于前端预览）。"""
    b64 = base64.b64encode(svg_content.encode('utf-8')).decode('ascii')
    return f'data:image/svg+xml;base64,{b64}'


def generate_thumbnail_from_template(
    template_dir: str,
    slide_file: str,
    output_path: str,
    size: int = 400,
) -> str:
    """
    从模板 SVG 生成缩略图。

    Args:
        template_dir: 模板目录（如 'government_blue'）
        slide_file: 幻灯片文件名（如 '01_cover.svg'）
        output_path: 输出 PNG 路径
        size: 缩略图宽度（高按 16:9 计算）

    Returns:
        输出 PNG 文件的路径
    """
    svg_path = os.path.join(template_dir, slide_file)
    if not os.path.exists(svg_path):
        raise FileNotFoundError(f'SVG not found: {svg_path}')

    height = int(size * 720 / 1280)
    return render_svg_file_to_png(svg_path, output_path, viewport_width=size, viewport_height=height, scale=1)


def cleanup():
    """清理 Playwright 浏览器实例（应用退出时调用）。"""
    global _browser, _playwright
    if _browser:
        _browser.close()
        _browser = None
        logger.info('[SVGRender] Browser closed')
    if _playwright:
        _playwright.stop()
        _playwright = None