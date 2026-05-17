"""
Style Analyzer Service - AI-powered design analysis for PPT templates
v0.6 Feature 3: Analyze uploaded PPT design style via AI
"""
import os
import io
import json
import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from services.ai_providers import get_text_provider
    from services.ppt_parser import PPTParser
    HAS_AI = True
except ImportError:
    HAS_AI = False


ANALYSIS_PROMPT = """你是一位专业PPT设计分析师。请分析以下PPT模板的设计风格，并输出结构化的设计元数据。

分析维度：
1. primary_color: 主色调（从模板的配色中提取最突出的颜色，用十六进制表示，如 #003371）
2. secondary_color: 辅助色（次要强调色）
3. font_title: 标题字体（从模板中提取的标题字体名称）
4. font_body: 正文字体
5. layout_type: 布局类型（两栏/单栏/图右文左/图上文下/三栏）
6. mood: 整体风格关键词（如：专业、学术、科技、庄重、温暖、复古）

请从以下PPT元数据中分析：
{context}

请直接输出JSON格式（不要有其他内容）：
{{"primary_color":"...", "secondary_color":"...", "font_title":"...", "font_body":"...", "layout_type":"...", "mood":"..."}}

如果无法确定某个字段，用"unknown"表示。"""


def _encode_thumbnail(thumb_bytes: bytes) -> str:
    """Encode thumbnail bytes to base64 for API transmission."""
    return base64.b64encode(thumb_bytes).decode('utf-8')


class StyleAnalyzer:
    """
    Analyze PPT design style using AI.
    """

    def __init__(self):
        if not HAS_AI:
            raise RuntimeError("AI providers not available")

    def analyze_pptx(self, pptx_path: str, thumb_size=(400, 225)) -> dict:
        """
        Analyze a PPTX file and return structured design metadata.
        Falls back to visual (thumbnail) analysis when python-pptx can't
        extract enough metadata from slide masters.
        """
        parser = PPTParser(pptx_path=pptx_path)
        metadata = parser.get_metadata()
        design_meta = metadata.get('design_meta', {})
        
        # Get first slide thumbnail for visual reference
        try:
            first_thumb = parser.get_thumbnail(0, *thumb_size)
            first_thumb_b64 = _encode_thumbnail(first_thumb)
        except Exception:
            first_thumb_b64 = None
        
        # Get all thumbnails
        all_thumbs = parser.get_all_thumbnails(*thumb_size)
        thumbs_b64 = {
            str(k): _encode_thumbnail(v) if v else None 
            for k, v in all_thumbs.items()
        }
        
        # Build context for AI analysis
        context = {
            'slide_count': metadata.get('slide_count', 0),
            'title_fonts': design_meta.get('title_fonts', []),
            'body_fonts': design_meta.get('body_fonts', []),
            'colors': design_meta.get('colors', []),
            'layout_type': design_meta.get('layout_type', '两栏'),
            'first_slide_bg': metadata.get('slides', [{}])[0].get('bg_color', '#FFFFFF') if metadata.get('slides') else '#FFFFFF',
        }
        
        # Detect sparse metadata — need visual fallback
        fonts_sparse = len(context['title_fonts']) == 0 and len(context['body_fonts']) == 0
        colors_sparse = len(context['colors']) <= 1
        need_visual_fallback = fonts_sparse or colors_sparse
        
        if need_visual_fallback:
            logger.info('[StyleAnalyzer] Sparse metadata detected (fonts/colors empty), using visual fallback')
            context['visual_fallback'] = True
            context['hint'] = 'Python-pptx could not extract font/color from slide masters. Please analyze the thumbnail images visually to determine the design style.'
        
        # Call AI for style analysis
        style_result = self._call_ai_analysis(context)
        
        # If AI analysis also fails, use sensible defaults derived from actual colors found
        if not style_result or 'primary_color' not in style_result:
            extracted_color = context.get('colors', ['#003371'])[0] or '#003371'
            style_result = {
                'primary_color': extracted_color,
                'secondary_color': '#005691',
                'font_title': 'Noto Sans SC',
                'font_body': 'Noto Sans SC',
                'layout_type': context.get('layout_type', '两栏'),
                'mood': '专业',
            }
            logger.info(f'[StyleAnalyzer] Using python-pptx extracted color as fallback: {extracted_color}')
        
        # Merge results
        result = {
            'primary_color': style_result.get('primary_color', '#003371'),
            'secondary_color': style_result.get('secondary_color', '#005691'),
            'font_title': style_result.get('font_title', 'Noto Sans SC'),
            'font_body': style_result.get('font_body', 'Noto Sans SC'),
            'layout_type': style_result.get('layout_type', context.get('layout_type', '两栏')),
            'mood': style_result.get('mood', '专业'),
            'slide_count': context['slide_count'],
            'slides_preview': thumbs_b64,
            'parse_method': 'visual_fallback' if need_visual_fallback else 'pptx_metadata',
        }
        
        return result

    def analyze_pptx_bytes(self, pptx_bytes: bytes, thumb_size=(400, 225)) -> dict:
        """Analyze PPTX from bytes (used for upload)."""
        parser = PPTParser(pptx_bytes=pptx_bytes)
        metadata = parser.get_metadata()
        design_meta = metadata.get('design_meta', {})
        
        context = {
            'slide_count': metadata.get('slide_count', 0),
            'title_fonts': design_meta.get('title_fonts', []),
            'body_fonts': design_meta.get('body_fonts', []),
            'colors': design_meta.get('colors', []),
            'layout_type': design_meta.get('layout_type', '两栏'),
            'first_slide_bg': metadata.get('slides', [{}])[0].get('bg_color', '#FFFFFF') if metadata.get('slides') else '#FFFFFF',
        }
        
        style_result = self._call_ai_analysis(context)
        
        all_thumbs = parser.get_all_thumbnails(*thumb_size)
        thumbs_b64 = {
            str(k): _encode_thumbnail(v) if v else None 
            for k, v in all_thumbs.items()
        }
        
        return {
            'primary_color': style_result.get('primary_color', '#003371'),
            'secondary_color': style_result.get('secondary_color', '#005691'),
            'font_title': style_result.get('font_title', 'Noto Sans SC'),
            'font_body': style_result.get('font_body', 'Noto Sans SC'),
            'layout_type': style_result.get('layout_type', context.get('layout_type', '两栏')),
            'mood': style_result.get('mood', '专业'),
            'slide_count': context['slide_count'],
            'slides_preview': thumbs_b64,
        }

    def _call_ai_analysis(self, context: dict) -> dict:
        """Call AI to analyze design style."""
        try:
            text_provider = get_text_provider(model='MiniMax-M2.7')
            prompt = ANALYSIS_PROMPT.format(context=json.dumps(context, ensure_ascii=False, indent=2))
            
            response = text_provider.generate_text(prompt, thinking_budget=0)
            response = response.strip()
            
            # Try to extract JSON
            json_str = None
            for pattern in [r'\{[\s\S]+\}', r'\[[\s\S]+\]']:
                import re
                m = re.search(pattern, response)
                if m:
                    json_str = m.group(0)
                    break
            
            if json_str:
                return json.loads(json_str)
            else:
                logger.warning(f"[StyleAnalyzer] No JSON found in AI response: {response[:100]}")
                return {}
                
        except Exception as e:
            logger.error(f"[StyleAnalyzer] AI analysis failed: {e}")
            return {}