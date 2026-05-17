"""
Page Content Planner - Smart content prioritization & enrichment for slide generation.

Solves three problems:
1. Content priority: Auto-select the richest source (outline vs description) as primary
2. Context enrichment: When content is thin, supplement with AI using neighbor pages
3. Page type detection: Identify cover/TOC/chapter/content/ending for style consistency
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Minimum total content length (chars) before triggering AI enrichment
MIN_CONTENT_LENGTH = 300

# Page type detection patterns
PAGE_TYPE_KEYWORDS = {
    'cover': ['封面', '首页', '标题页', 'title slide', 'cover'],
    'toc': ['目录', '大纲', 'contents', 'agenda', '议程', '索引'],
    'chapter': ['章节', '部分', 'part', 'chapter', '分隔', 'section divider'],
    'ending': ['结束', '感谢', '封底', '谢谢', 'thank', 'ending', '结语', '致谢'],
}


def detect_page_type(outline: str, description: str, page_index: int, total_pages: int) -> str:
    """
    Auto-detect page type: cover, toc, chapter, content, or ending.
    """
    combined = f"{outline} {description}".lower()

    # Position-based heuristics
    if page_index == 0:
        return 'cover'
    if page_index == total_pages - 1:
        return 'ending'
    if page_index == 1:
        return 'toc'

    # Content-based detection
    for ptype, keywords in PAGE_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in combined:
                return ptype

    # Check if this looks like a chapter/section divider (short, structural)
    total_len = len(outline.strip()) + len(description.strip())
    if total_len < 200 and any(kw in combined for kw in ['章节', 'part', '部分', '分隔']):
        return 'chapter'

    return 'content'


def _text_density_score(text: str) -> float:
    """
    Score how information-dense a text is.
    Higher score = more detailed, more content-rich.
    Considers: length, sentence count, numeric data, bullet points, structured content.
    """
    if not text or not text.strip():
        return 0.0

    t = text.strip()
    score = 0.0

    # Base: length (capped at 2000 chars)
    score += min(len(t), 2000) * 0.001

    # Sentence variety: more sentences = more information
    import re
    sentences = re.split(r'[。！？；\n]', t)
    sentences = [s.strip() for s in sentences if s.strip()]
    score += min(len(sentences), 20) * 0.05

    # Structured content: bullet points, numbered lists, key-value pairs
    bullet_count = len(re.findall(r'[•·●○▸►▪▹▶✓✔✗✘☐☑☆★]', t))
    numbered_count = len(re.findall(r'\d+[\.\、\)）]', t))
    score += (bullet_count + numbered_count) * 0.1

    # Data richness: numbers, percentages, dates
    data_count = len(re.findall(r'\d+%|\d+\.\d+|\d{4}年|\d+月', t))
    score += data_count * 0.05

    # Key-value structure indicators
    kv_count = len(re.findall(r'[：:]\s*\S', t))
    score += kv_count * 0.03

    return score


def plan_page_content(
    outline_content: str,
    description_content: str,
    page_index: int,
    total_pages: int,
    project_idea: str = '',
    neighbor_summaries: Optional[list[str]] = None,
) -> dict:
    """
    Plan the content priority and enrichment strategy for a single page.

    Args:
        outline_content: The page outline (from user or AI-generated)
        description_content: The page detailed description
        page_index: 0-based page index
        total_pages: Total number of pages in the project
        project_idea: Overall project theme/idea
        neighbor_summaries: Optional summaries of neighboring pages for context

    Returns:
        dict with keys:
            primary_content: The main content to use (richest source)
            auxiliary_content: Secondary reference content
            page_type: Detected page type
            needs_enrichment: Whether AI enrichment is recommended
            enrichment_context: Context for AI enrichment if needed
            detail_level: 'rich' | 'adequate' | 'thin'
    """
    outline = (outline_content or '').strip()
    description = (description_content or '').strip()

    # Score both sources
    outline_score = _text_density_score(outline)
    desc_score = _text_density_score(description)

    # The more detailed source becomes primary
    if desc_score >= outline_score * 1.2:
        # Description is significantly richer
        primary = description
        auxiliary = outline
        logger.info(
            f'[Planner] Page {page_index+1}: description is primary '
            f'(score: {desc_score:.1f} vs {outline_score:.1f})'
        )
    elif outline_score >= desc_score * 1.2:
        # Outline is significantly richer
        primary = outline
        auxiliary = description
        logger.info(
            f'[Planner] Page {page_index+1}: outline is primary '
            f'(score: {outline_score:.1f} vs {desc_score:.1f})'
        )
    else:
        # Roughly equal — use outline as primary (user intent), description as supplement
        primary = outline
        auxiliary = description

    # Detect page type
    page_type = detect_page_type(outline, description, page_index, total_pages)

    # Check if content is too thin
    total_len = len(primary) + len(auxiliary)
    if total_len < MIN_CONTENT_LENGTH:
        detail_level = 'thin'
        needs_enrichment = True
        enrichment_context = _build_enrichment_context(
            primary, auxiliary, page_index, total_pages,
            project_idea, neighbor_summaries, page_type
        )
    elif total_len < 600:
        detail_level = 'adequate'
        needs_enrichment = False
        enrichment_context = ''
    else:
        detail_level = 'rich'
        needs_enrichment = False
        enrichment_context = ''

    return {
        'primary_content': primary,
        'auxiliary_content': auxiliary,
        'page_type': page_type,
        'needs_enrichment': needs_enrichment,
        'enrichment_context': enrichment_context,
        'detail_level': detail_level,
        'primary_source': 'description' if desc_score >= outline_score * 1.2 else 'outline',
    }


def _build_enrichment_context(
    primary: str,
    auxiliary: str,
    page_index: int,
    total_pages: int,
    project_idea: str,
    neighbor_summaries: Optional[list[str]],
    page_type: str,
) -> str:
    """Build context prompt for AI-based content enrichment."""
    parts = []

    if project_idea:
        parts.append(f"项目主题：{project_idea[:200]}")

    parts.append(f"本页类型：{_page_type_cn(page_type)}")
    parts.append(f"页面位置：第 {page_index + 1} 页 / 共 {total_pages} 页")

    if primary:
        parts.append(f"现有大纲/描述：{primary[:300]}")
    if auxiliary:
        parts.append(f"补充参考：{auxiliary[:300]}")

    if neighbor_summaries:
        for i, summary in enumerate(neighbor_summaries):
            if summary:
                pos = page_index - 1 + i  # -1, 0, +1 relative
                parts.append(f"第{pos + 2}页摘要：{summary[:200]}")

    parts.append(
        "\n请根据以上上下文，为本页幻灯片补充完善内容，生成一份适合作为PPT单页的"
        "详细内容描述（含标题、要点、数据支撑、视觉建议），不要重复已有内容。"
    )

    return '\n'.join(parts)


def _page_type_cn(ptype: str) -> str:
    _map = {
        'cover': '封面页',
        'toc': '目录页',
        'chapter': '章节分隔页',
        'content': '内容页',
        'ending': '封底/结束页',
    }
    return _map.get(ptype, '内容页')


def get_page_type_style_guidance(page_type: str, template_name: str = 'government_blue') -> str:
    """
    Generate style guidance specific to the page type, ensuring consistency
    across same-type pages within a project.
    """
    common_rules = """
## 设计一致性要求（极其重要）
- 本项目所有页面必须使用统一的设计语言：相同的主色调、相同的字体系统、相同的装饰元素风格
- 标题栏、页码位置、底部装饰线等结构性元素必须在所有内容页保持完全一致
- 卡片样式、图标风格、分隔线样式等细节元素必须在所有页面统一
"""

    type_specific = {
        'cover': """
## 封面页特殊要求
- 必须使用深蓝色渐变背景（从深蓝到科技蓝），体现宏大、专业感
- 主标题字号 48-56px，白色粗体，居中或左对齐
- 包含：主标题、副标题（如有）、组织名称、日期
- 使用几何装饰元素（圆形、线条、网格纹理）增加科技感和层次
- 不得有内容溢出或文字重叠
- 右下角或底部放置组织LOGO位置
""",
        'toc': """
## 目录页特殊要求
- 使用浅蓝渐变背景，白色卡片式布局
- 列出所有章节（通常4-6个），每个章节用圆形编号+标题+简短描述
- 编号圆圈使用主色调，文字使用深色
- 章节之间用细线或虚线连接，形成清晰的信息流
- 整体布局居中，留白充足
- 必须在视觉上与其他项目的目录页保持一致的设计语言
""",
        'chapter': """
## 章节分隔页特殊要求
- 使用深蓝色渐变背景（与封面呼应但更简洁）
- 大号章节编号（半透明+描边效果），配合章节标题
- 可包含简短的章节概述文字
- 装饰元素使用径向渐变光晕或几何图形
- 与封面页共享相同的深蓝色调和几何装饰语言
""",
        'content': """
## 内容页通用要求
- 使用白色或浅灰蓝色背景（#F5F7FA 或 #FFFFFF）
- 顶部必须有统一的标题栏：左侧章节编号方块+标题文字，右侧可选LOGO位置
- 标题栏下方为内容区，根据内容量选择合适的布局模式（单栏/双栏/三栏/卡片网格）
- 底部有页码和装饰线
- 所有内容页的标题栏样式、页码位置、边距必须完全一致
""",
        'ending': """
## 封底/结束页特殊要求
- 使用深蓝色渐变背景（与封面完全一致的色调）
- 居中放置感谢文字（中文+英文）
- 可包含联系信息、二维码位置、公司信息
- 底部加公司全称和网址
- 波浪曲线或几何图形装饰，与封面形成首尾呼应
- 必须与封面使用完全相同的深蓝渐变背景色值
""",
    }

    guidance = common_rules + type_specific.get(page_type, type_specific['content'])

    # Add visual quality requirements
    guidance += """
## 视觉质量要求
- 图标和装饰元素必须精心设计，使用多色渐变、层叠效果、半透明叠加等手法
- 避免单调的纯色平面图标，优先使用：双色渐变图标、线面结合图标、微立体图标
- 卡片使用微妙阴影（通过半透明深色矩形偏移实现），增强层次感
- 数据展示区域使用色块分区、进度条、对比色强调等手法
- 文字排版要有节奏感：标题→副标题→正文→注释，形成清晰的视觉层级
- 留白要充分：内容区占比不超过70%，避免信息过载
- 装饰元素要克制：每页装饰元素不超过3处，避免喧宾夺主
- 所有图形元素必须使用标准SVG元素（rect/circle/path/polygon），不得使用foreignObject
"""

    return guidance


def build_unified_design_brief(
    project_idea: str,
    template_name: str,
    primary_color: str,
    accent_color: str = '#00875A',
    secondary_color: str = '#005691',
) -> str:
    """
    Build a unified design brief shared across ALL pages of a project.
    This ensures visual consistency.
    """
    return f"""
## 项目统一设计规范（所有页面必须遵守）

### 色彩系统
- 主色：{primary_color}（用于标题、重点元素、章节编号、顶部装饰线）
- 强调色：{accent_color}（用于数据高亮、关键信息标注、成功/正向标识）
- 副色：{secondary_color}（用于链接、次要强调、辅助图形）
- 背景色：白色 #FFFFFF 或浅灰蓝 #F5F7FA（用于内容页）
- 深色背景：主色深色调（用于封面/章节分隔/封底页）
- 文字色：深色 #1A1A1A（正文）、#4A5568（辅助文字）、白色（深色背景上）

### 结构性元素（所有内容页统一）
- 顶部装饰线：6px高，主色渐变条，横跨全宽
- 标题栏：y=30 至 y=80，左侧章节编号方块(50x50px,主色填充,白色数字)，右侧标题文字(28px粗体)
- 底部：页码(y≈690,右对齐) + 4px装饰线(y≈716)
- 内容区：y=100 至 y=670

### 字体规范（全项目统一）
- 中文标题：Noto Sans SC Bold 或 Microsoft YaHei Bold
- 中文正文：Noto Sans SC Regular 或 Microsoft YaHei
- 数字/英文：system-ui 或 Inter
- 字号层级：大标题 28-52px / 小标题 24px / 正文 16-18px / 注释 14px

### 图标/装饰风格（全项目统一）
- 图标风格：线面结合、双色渐变、微立体感
- 不使用纯色平面简单图标
- 装饰元素使用几何图形（圆形、圆角矩形、线条）配合透明度叠加
- 每页装饰元素不超过3处，保持克制

### 项目主题
{project_idea[:300]}

### 模板风格
{template_name}
"""
