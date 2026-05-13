"""
Outline Generator Service - Extracts PPT outlines from project idea text
Used when pages are created with empty outline_content and the user provided rich content.
"""
import re


_TOPIC_KEYWORDS = [
    '背景', '目标', '分析', '方法', '路径', '成果', '总结', '展望', '建议',
    '框架', '策略', '设计', '创新', '服务', '价值', '技术', '平台',
    '场景', '定义', '挑战', '路线', '概述', '简介', '前言', '目录',
    '现状', '问题', '痛点', '方案', '架构', '生态',
    '智能', '调度', '诊断', '监测', '安全', '营销', '客户', '碳排', '网络',
    '实施', '路线图',
]

_SECTION_KEYWORD_PAIRS = [
    ('背景', '背景'), ('目标', '背景'), ('现状', '分析'), ('问题', '分析'),
    ('痛点', '分析'), ('分析', '分析'), ('方法', '方法'), ('路径', '方法'),
    ('策略', '方法'), ('设计', '方法'), ('方案', '方法'), ('架构', '方法'),
    ('成果', '成果'), ('效果', '成果'), ('价值', '成果'), ('展示', '成果'),
    ('总结', '总结'), ('展望', '总结'), ('建议', '总结'), ('风险', '总结'),
    ('挑战', '总结'), ('场景', '成果'), ('智能体', '成果'), ('技术', '方法'),
    ('实施', '方法'), ('路线', '方法'), ('安全', '成果'), ('营销', '成果'),
]


def _is_meta_field(line: str) -> bool:
    """Skip field-label lines that are metadata, not content."""
    return bool(re.match(r'^(标题|副标题|内容|要点|视觉|痛点|智能体|实用|核心|场景|技术|实施|风险|关键|实用化|底层|视觉单元|配图|备注)[：:]', line.strip()))


def generate_outlines_from_idea(idea_text: str, max_pages: int = 12) -> list[dict]:
    """
    Parse idea_text and extract PPT-ready outlines.

    Handles the common "第X页：标题\n内容要点：\n- item1\n- item2\n..."
    user format. Each "第X页：标题" block produces at most one outline item.

    Returns list of {outline_content, part} dicts.
    """
    if not idea_text or len(idea_text.strip()) < 10:
        return default_outlines(max_pages)

    lines = idea_text.strip().split('\n')

    # ------------------------------------------------------------------
    # Strategy 1: Parse "第X页：标题" sections
    # ------------------------------------------------------------------
    page_items = []
    current_title = None
    current_part = '概述'
    content_lines = []
    in_content_block = False

    def _flush_content_lines(title, part, lines):
        """Extract the best outline from a page section's content."""
        if not title:
            return None

        clean_title = title.strip()
        # A title is meaningful if it's a real description (not just a label like "第1页")
        meaningful_title = (
            len(clean_title) >= 2 and
            not _is_meta_field(clean_title) and
            not clean_title.startswith('第')
        )

        # If we have a meaningful page title, use it even if content_lines is empty
        # (handles "第1页：项目背景\n第2页：现状分析" with no bullet content)
        if meaningful_title:
            raw_content = '\n'.join(lines).strip()
            return {'outline_content': clean_title[:80], 'part': part, 'page_instruction': raw_content}

        # No meaningful title — need content_lines to find a candidate
        if not lines:
            # Last resort: use the title as-is if we have nothing else
            if clean_title:
                return {'outline_content': clean_title[:80], 'part': part}
            return None

        candidates = []
        in_content_block = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                in_content_block = False
                continue
            if _is_meta_field(stripped):
                continue

            # "内容要点：" / "主要内容：" lines signal content block
            if re.match(r'^(内容要点|主要内容|要点|核心内容|摘要)[：:]?\s*$', stripped):
                in_content_block = True
                continue

            # Bullets — only count inside content block
            if stripped.startswith(('•', '-', '*', '·', '◇', '○', '●', '►', '▸')):
                if in_content_block:
                    text = stripped.lstrip('-*•·◇○●►▸ ')
                    if text and len(text) >= 6:
                        candidates.append(text[:80])
                continue

            # Skip short lines
            if len(stripped) < 6:
                continue

            # Numbered sub-items "1. text" or "(a) text"
            sub_m = re.match(r'^\s*[a-zA-Z0-9\u4e00-\u9fff]{1,3}[\.、\)）]\s*(.+)$', stripped.strip())
            if sub_m:
                text = sub_m.group(1).strip()
                if text and len(text) >= 6:
                    candidates.append(text[:80])
                continue

            # Generic line
            if 6 <= len(stripped) <= 80:
                candidates.append(stripped[:80])

        if candidates:
            best = max(candidates, key=lambda x: len(x))
            return {'outline_content': best, 'part': part}
        return None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            content_lines.append('')
            in_content_block = False
            continue

        # "第X页：标题" heading → flush previous section
        page_match = re.match(r'^第([一二三四五六七八九十零0-9]+)\s*页\s*[:：]\s*(.+)$', stripped)
        if page_match:
            if current_title is not None:
                item = _flush_content_lines(current_title, current_part, content_lines)
                if item:
                    page_items.append(item)

            current_title = page_match.group(2).strip()
            current_part = guess_part(current_title) if current_title else '概述'
            content_lines = []
            in_content_block = False
            continue

        content_lines.append(line)

    # Flush last page
    if current_title is not None:
        item = _flush_content_lines(current_title, current_part, content_lines)
        if item:
            page_items.append(item)

    # Deduplicate
    seen = set()
    unique = []
    for s in page_items:
        key = s['outline_content'][:30]
        if key not in seen and len(s['outline_content']) >= 2:
            seen.add(key)
            unique.append(s)

    if len(unique) >= 1:
        return unique[:max_pages]

    # ------------------------------------------------------------------
    # Strategy 2: Numbered sections without "第X页" (一、内容 / 1. 内容)
    # ------------------------------------------------------------------
    fallback_sections = []
    current_part = ''
    for line in lines:
        line = line.strip()
        if not line:
            current_part = ''
            continue
        if len(line) < 4 or line.startswith('```') or line.startswith('---'):
            continue
        if line.startswith(('•', '-', '*', '·', '◇', '○', '●', '►', '▸', '–', '—', '－')):
            continue
        if re.match(r'^\s*[a-zA-Z0-9]{1,3}[\.、\)]', line.strip()):
            continue
        if re.match(r'^\s*[<《【][^】》]+[》】>]?\s*$', line.strip()):
            continue
        if _is_meta_field(line):
            continue
        if len(line) < 6 and not any(kw in line for kw in _TOPIC_KEYWORDS):
            continue

        # Chinese numeral sections "一、内容"
        cn_match = re.match(r'^[一二三四五六七八九十]+[、.．]\s*(.+)$', line)
        if cn_match:
            title = cn_match.group(1).strip()
            if 2 <= len(title) <= 60:
                fallback_sections.append({'outline_content': title[:80], 'part': current_part})
            continue

        # Arabic numeral sections "1. 内容"
        num_match = re.match(r'^[0-9]+[.、)）]\s*(.+)$', line)
        if num_match:
            title = num_match.group(1).strip()
            if 2 <= len(title) <= 60:
                fallback_sections.append({'outline_content': title[:80], 'part': current_part})
            continue

        # Topic keyword at start
        if 4 <= len(line) <= 40 and any(line.startswith(kw) for kw in _TOPIC_KEYWORDS):
            fallback_sections.append({'outline_content': line[:80], 'part': current_part})

    seen2 = set()
    unique2 = []
    for s in fallback_sections:
        key = s['outline_content'][:30]
        if key not in seen2 and len(s['outline_content']) >= 4:
            seen2.add(key)
            unique2.append(s)

    if len(unique2) >= 2:
        return unique2[:max_pages]

    # ------------------------------------------------------------------
    # Strategy 3: Keyword anywhere in content
    # ------------------------------------------------------------------
    if len(idea_text) > 200:
        found3 = []
        seen3 = set()
        for kw, part in _SECTION_KEYWORD_PAIRS:
            if kw in idea_text:
                idx = idea_text.index(kw)
                snippet = idea_text[max(0, idx - 5):min(len(idea_text), idx + len(kw) + 20)].strip()
                heading_m = re.search(r'[^，。\n]{0,30}' + re.escape(kw) + r'[^，。\n]{0,20}', snippet)
                if heading_m:
                    clean = heading_m.group(0).strip()[:60]
                    if clean and len(clean) >= 4 and clean[:15] not in seen3:
                        seen3.add(clean[:15])
                        found3.append({'outline_content': clean, 'part': part})
        if len(found3) >= 2:
            return found3[:max_pages]

    return generate_from_content_structure(idea_text, max_pages)


def generate_from_content_structure(text: str, max_pages: int) -> list[dict]:
    """Extract section structure from long-form content"""
    parts = re.split(r'\n(?=第[一二三四]部分)|\n(?=【[^】]+】)|\n\n+', text)
    sections = []
    seen = set()

    for part in parts[:max_pages * 2]:
        part = part.strip()
        if len(part) < 15:
            continue
        lines = [l.strip() for l in part.split('\n') if l.strip() and len(l.strip()) > 5]
        for l in lines[:3]:
            if l.startswith(('•', '-', '*', '·', '1.', '2.', 'a.', 'A.')):
                continue
            if 6 <= len(l) <= 80:
                key = l[:20]
                if key not in seen:
                    seen.add(key)
                    sections.append({'outline_content': l[:80], 'part': guess_part(l)})
                break
        if len(sections) >= max_pages:
            break

    return sections[:max_pages] if len(sections) >= 3 else chunk_content(text, max_pages)


def chunk_content(text: str, max_pages: int) -> list[dict]:
    """Last resort: split long content into rough chunks"""
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'`.*?`', '', text)
    chunks = re.split(r'\n\n+', text)
    result = []
    seen = set()
    for chunk in chunks[:max_pages * 2]:
        chunk = chunk.strip()
        if len(chunk) < 20:
            continue
        first_line = chunk.split('\n')[0].strip()[:60]
        if len(first_line) < 4:
            first_line = chunk[:60]
        key = first_line[:20]
        if key not in seen:
            seen.add(key)
            result.append({'outline_content': first_line, 'part': guess_part(first_line)})
        if len(result) >= max_pages:
            break
    return result if result else default_outlines(max_pages)


def guess_part(outline_text: str) -> str:
    """Guess section name from outline text"""
    text = outline_text.lower()
    if any(k in text for k in ['背景', '概述', '简介', '前言', '目标', '封面']): return '背景'
    if any(k in text for k in ['现状', '分析', '问题', '痛点', '诊断', '洞察']): return '分析'
    if any(k in text for k in ['方法', '路径', '策略', '设计', '方案', '创新', '实施', '技术', '架构', '平台']): return '方法'
    if any(k in text for k in ['成果', '展示', '效果', '价值', '案例', '场景', '应用']): return '成果'
    if any(k in text for k in ['总结', '展望', '建议', '结尾', '结论', '风险', '挑战']): return '总结'
    return '概述'


def default_outlines(n: int = 5) -> list[dict]:
    """Return default outline structure"""
    defaults = [
        {'outline_content': '项目背景与目标', 'part': '背景'},
        {'outline_content': '现状分析', 'part': '分析'},
        {'outline_content': '实施路径与方法', 'part': '方法'},
        {'outline_content': '成果展示', 'part': '成果'},
        {'outline_content': '总结与展望', 'part': '总结'},
    ]
    return defaults[:n]