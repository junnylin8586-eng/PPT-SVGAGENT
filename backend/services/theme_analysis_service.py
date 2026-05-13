"""
Theme Analysis Service - AI-powered PPT outline generation from user descriptions

Supports:
  - Short input (<100 chars): LLM expands to a reasonable structure
  - Long/detailed input with "第X页" markers: LLM understands the full structure, then
    generates per-page {part, outline_content, page_instruction} for each page
  - HTTP trigger + SSE streaming for real-time progress
"""
import re
import json
import logging
from typing import Generator, Dict, List, Optional

logger = logging.getLogger(__name__)

# MiniMax models emit <think> tags that must be stripped before JSON parsing
def strip_think_tags(text: str) -> str:
    """"Remove MiniMax think tags and their content from LLM output."""
    return re.sub(r'<think>[\s\S]*?</think>', '', text)

# ============================================================================
# PROMPTS
# ============================================================================

SYSTEM_PROMPT = """你是一个PPT结构分析助手，专门理解用户提供的详细主题描述，提取每个页面的核心信息。

## 你的任务

用户会输入一个PPT主题描述，包含多个"第X页"标记的页面内容。

你必须：
1. 理解每个页面的核心主题和内容
2. 为每个页面生成结构化的大纲数据

## 输出格式（严格JSON数组）

```json
[
  {
    "page": 1,
    "part": "背景/分析/方法/成果/总结",
    "outline_content": "页面标题（简洁，20字以内）",
    "page_instruction": "【关键】这是给AI生成PPT页面的完整提示词，必须包含：该页的核心主题、要展示的关键内容、布局建议、配色/风格提示。所有内容需要具体、有信息量，让AI能直接根据这段描述生成高质量PPT页面。",
    "key_points": ["要点1", "要点2"],
    "layout_hint": "两栏/单栏/图右文左"
  }
]
```

## 章节类型定义

- 背景：封面、目标、市场背景、概述
- 分析：现状、问题、数据、趋势、竞品洞察
- 方法：实施路径、技术方案、建设内容
- 成果：效果、案例、价值展示、排名
- 总结：结论、建议、展望、下一步

## page_instruction 写作规范（最重要）

这是AI生成PPT页面的唯一依据。必须包含：
1. 该页的核心主题是什么
2. 需要展示哪些具体内容（数据/案例/结论）
3. 布局建议（两栏/左图右文/上下结构等）
4. 风格/配色提示（如：商务蓝色、简洁大气、数据可视化风格）

示例（差的page_instruction）："概述"
示例（好的page_instruction）："本页面展示2026年手机市场整体趋势，包含销量排名TOP10产品数据、市场份额分布图。重点使用图表可视化，左侧柱状图展示TOP10排名，右侧饼图展示品牌份额。整体风格简洁商务蓝，适合高管汇报。"

## 生成原则

1. 严格按用户指定的页数生成，不要增删
2. 每个page_instruction要具体、有信息量，避免空泛
3. part分类要准确反映页面真实内容
4. outline_content要简洁有力，能一眼看出该页核心主题"""

STRUCTURED_USER_PROMPT_TEMPLATE = """请分析以下PPT主题描述，提取每个页面的结构化大纲。

【核心规则】用户已经明确指定了完整的页面结构，你必须严格遵循：
1. 从"第X页"标记中提取总页数（例如：描述了第1页到第15页 → 生成恰好15页，不要多也不要少）
2. 每个页面的outline_content = 该"第X页"后的标题/主题
3. 每个页面的page_instruction = 该页面描述中的具体内容要点（内容要点是什么，就原样保留什么，不要自行发挥）
4. part分类要准确反映该页内容属于背景/分析/方法/成果/总结中的哪一类

格式识别示例：
  输入"第1页：封面\n第2页：研究背景..." → 识别为2页
  输入"第1页：xxx\n  标题：yyy\n  内容：zzz" → outline_content="xxx"，page_instruction="标题：yyy\n内容：zzz"
  输入"第1页：xxx\n  内容要点：...多条..." → page_instruction完整保留所有要点

生成原则：
- 用户说几页就生成几页（不多不少）
- page_instruction必须引用用户在"内容要点"中写的具体内容，不要自己编造数据或案例
- outline_content要简洁（20字以内），直接反映该页主题

主题描述：
{theme_text}

请直接输出JSON数组，不要包含任何解释或说明文字。"""

SHORT_USER_PROMPT_TEMPLATE = """请为以下PPT主题生成详细大纲，每个页面需要包含完整的page_instruction：

主题描述：
{theme_text}

请直接输出JSON数组，不要包含任何解释或说明文字。"""


def parse_llm_json_response(text: str) -> List[Dict]:
    """从LLM响应中解析JSON大纲列表

    支持两种格式：
    1. 严格JSON数组（优先）
    2. LLM自然文本输出（降级）：形如 "第X页：标题 - 描述" 或 "第X页\n- part: xxx\n- outline: xxx"
    """
    text = strip_think_tags(text).strip()

    # 去掉 Markdown 代码块包装
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]+?)```', text)
    if code_block_match:
        text = code_block_match.group(1).strip()

    # 迭代提取所有 JSON 数组（处理 LLM 分段输出 JSON 的情况）
    all_items = []
    decoder = json.JSONDecoder()
    pos = 0
    while pos < len(text):
        try:
            obj, end_pos = decoder.raw_decode(text, pos)
            if isinstance(obj, list):
                all_items.extend(obj)
            pos = end_pos
        except json.JSONDecodeError:
            pos += 1

    if all_items:
        return all_items

    # JSON解析失败 → 尝试从自然文本解析LLM的输出
    outlines = parse_text_format(text)
    if outlines:
        return outlines

    return parse_fallback(text)


def parse_text_format(text: str) -> List[Dict]:
    """从LLM自然文本输出中提取大纲（JSON解析失败时的降级）

    LLM常输出以下自然文本格式：
      格式A: 第1页：标题 - 描述
      格式B: 第1页\n- part: xxx\n- outline_content: xxx\n- page_instruction: xxx
      格式C: ## 第1页 标题\n**part**: xxx\n**描述**: xxx
    """
    outlines = []
    lines = text.split('\n')

    # 预扫描：将多行格式（格式B/C）合并，再逐块处理
    # 先把 text 按 "第X页" 模式分段
    page_blocks = re.split(r'(?=第[一二三四五六七八九十零0-9]+\s*页)', text)

    for block in page_blocks:
        block = block.strip()
        if not block:
            continue

        # 从块中提取页码
        page_match = re.match(r'第([一二三四五六七八九十零0-9]+)\s*页', block)
        if not page_match:
            continue

        cn_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10, '零': 0}
        num_str = page_match.group(1)
        try:
            page_num = cn_map[num_str] if num_str in cn_map else int(num_str)
        except ValueError:
            page_num = len(outlines) + 1

        # 提取 part（支持多种字段名）
        part_match = re.search(r'(?:part|章节|类型|分类)[:：]\s*([^\n，,]+)', block)
        part = part_match.group(1).strip() if part_match else guess_part(block)
        # 清理part值（只保留关键词）
        for kw in ['背景', '分析', '方法', '成果', '总结', '概述', '目录']:
            if kw in part:
                part = kw
                break
        if part not in ('背景', '分析', '方法', '成果', '总结', '概述', '目录'):
            part = guess_part(block)

        # 提取 outline_content（支持多种字段名）
        outline_match = re.search(r'(?:outline_content|title|标题|名称)[:：]\s*["\']?([^"\'\n，,：:]{2,50})["\']?', block)
        outline_content = ''
        if outline_match:
            outline_content = outline_match.group(1).strip()
        else:
            # 格式A: "第1页：标题 - 描述"，尝试从第一行提取
            first_line = block.split('\n')[0]
            header_rest = re.sub(r'^第[一二三四五六七八九十零0-9]+\s*页\s*[:：]?\s*', '', first_line)
            if header_rest and len(header_rest) >= 2:
                # 去掉 "- 描述" 或 "：描述" 部分，取标题
                title_candidate = re.split(r'\s*[-－]\s*', header_rest)[0]
                title_candidate = title_candidate.strip().rstrip('：:')
                if len(title_candidate) >= 2:
                    outline_content = title_candidate[:50]

        # 提取 page_instruction（支持多种字段名）
        pi_match = re.search(r'(?:page_instruction|描述|说明|内容|详情)[:：]\s*(.{10,500})', block)
        page_instruction = pi_match.group(1).strip() if pi_match else block[:200]

        if outline_content or page_instruction:
            outlines.append({
                'page': page_num,
                'part': part,
                'outline_content': outline_content or f'第{page_num}页',
                'page_instruction': page_instruction,
                'key_points': [],
                'layout_hint': '两栏'
            })

    # 去重：如果解析出重复页号，保留第一个
    seen = set()
    result = []
    for o in outlines:
        if o['page'] not in seen:
            seen.add(o['page'])
            result.append(o)

    return result


def parse_fallback(text: str) -> List[Dict]:
    """解析完全失败时的最终降级：逐行解析"""
    outlines = []
    lines = text.split('\n')
    page_num = 1
    for line in lines:
        line = line.strip()
        if not line or len(line) < 4:
            continue
        if line.startswith('```') or line.startswith('---'):
            continue
        cleaned = re.sub(r'^[-*•]\s+', '', line)
        if len(cleaned) >= 4:
            outlines.append({
                'page': page_num,
                'part': guess_part(cleaned),
                'outline_content': cleaned[:80],
                'key_points': [],
                'layout_hint': '两栏',
                'page_instruction': cleaned
            })
            page_num += 1
    return outlines


def guess_part(text: str) -> str:
    """根据标题或页面描述文本推断章节类型"""
    t = text.lower()
    # 背景/封面/目录/战略目标（最优先，避免被"展示"/"数据"等通用词抢断）
    bg_keywords = ['背景', '概述', '简介', '前言', '目标', '封面', '目录', '战略', '规划', '计划']
    if any(k in t for k in bg_keywords): return '背景'
    # 成果类（展示结果）
    result_keywords = ['成果', '效果', '价值', '案例', '总览', '展示', '活跃', '渗透', '覆盖', '提升', '增长']
    if any(k in t for k in result_keywords): return '成果'
    # 分析 - 现状/问题/数据/市场
    analysis_keywords = ['现状', '分析', '问题', '诊断', '痛点', '挑战', '趋势', '洞察', '排名', '市场', '对标', '差距', '竞品', '成熟度']
    if any(k in t for k in analysis_keywords): return '分析'
    # 方法 - 技术/实施/路径/策略/建设
    method_keywords = ['方法', '路径', '策略', '设计', '方案', '创新', '实施', '技术', '建设', '转型', '举措', '任务', '治理', '变革', '平台']
    if any(k in t for k in method_keywords): return '方法'
    # 总结 - 结论/Q&A/附录/术语/风险/保障
    summary_keywords = ['总结', '展望', '建议', '未来', '下一步', '结语', '结论', 'q&a', '附录', '术语', '参考', '风险', '保障', '预测', '里程碑', '效益']
    if any(k in t for k in summary_keywords): return '总结'
    return '概述'


def detect_input_mode(text: str) -> str:
    """判断输入类型 - 优先检查页面编号模式，再检查长度"""
    text = text.strip()
    # 检查页面编号模式（优先于长度检查，避免短文本被错误分类）
    if re.search(r'第[一二三四五六七八九十零0-9]+\s*页', text):
        return 'detailed_page_numbered'
    if re.search(r'^\s*第[一二三四五六七八九十]+[、.．]', text, re.MULTILINE):
        return 'detailed_page_numbered'
    if re.search(r'^#{1,3}\s+.{2,20}$', text, re.MULTILINE):
        return 'detailed_markdown'
    # 短文本直接返回
    if len(text) < 100:
        return 'short'
    if text.count('\n\n') >= 3:
        return 'detailed_structured'
    return 'detailed_general'



def clean_theme_text(text: str) -> str:
    """清理主题文本中的复制粘贴残留词，避免干扰LLM理解"""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # 跳过残留词行
        if stripped.lower() in ('plain', '复制', 'markdown', 'html', '代码', 'text', 'json'):
            continue
        # 跳过指令性行（生成PPT之类的指令不是页面内容）
        if stripped.startswith('生成') or stripped.startswith('请生成') or stripped.startswith('创建'):
            continue
        # 跳过含"复制"且很短的行
        if '复制' in stripped and len(stripped) < 20:
            continue
        cleaned.append(line)
    return '\n'.join(cleaned)


def build_analysis_prompt(theme_text: str) -> tuple[str, str]:
    """构建发送给LLM的提示词"""
    theme_text = clean_theme_text(theme_text)
    mode = detect_input_mode(theme_text)
    if mode == 'detailed_page_numbered':
        user_prompt = STRUCTURED_USER_PROMPT_TEMPLATE.format(theme_text=theme_text)
    else:
        user_prompt = SHORT_USER_PROMPT_TEMPLATE.format(theme_text=theme_text)
    return SYSTEM_PROMPT, user_prompt


def split_pages_from_theme_text(theme_text: str) -> List[Dict]:
    """
    【降级备用】不用LLM，纯regex切割"第X页"块。
    返回每个page的原始信息，part/outline_content/page_instruction由LLM生成时填入。
    """
    lines = theme_text.split('\n')
    pages = []
    current_page_num = None
    current_title = None
    current_body_lines = []
    started = False

    def save_page(num, title, body_lines):
        if num is None:
            return
        title = title or f'第{num}页'
        body = '\n'.join(body_lines)
        kp = extract_key_points(title, body)
        pages.append({
            'page': num,
            'part': guess_part(title),
            'outline_content': title[:40],
            'page_instruction': body,
            'key_points': kp,
            'layout_hint': '两栏'
        })

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if line_stripped.startswith('```'):
            continue

        header_match = re.match(r'^第([一二三四五六七八九十零0-9]+)\s*页\s*[:：]?\s*(.*)$', line_stripped)
        if header_match:
            if started:
                save_page(current_page_num, current_title, current_body_lines)
            cn_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10, '零': 0}
            num_str = header_match.group(1)
            try:
                if num_str in cn_map:
                    current_page_num = cn_map[num_str]
                else:
                    current_page_num = int(num_str)
            except ValueError:
                current_page_num = len(pages) + 1
            header_rest = header_match.group(2).strip() if header_match.group(2) else ''
            if header_rest and len(header_rest) <= 40 and not header_rest.startswith('生成') and not header_rest.startswith('请生成'):
                current_title = header_rest
                current_body_lines = []
            else:
                current_title = None
                current_body_lines = [header_rest] if header_rest else []
            started = True
        elif started:
            cleaned = re.sub(r'^[-*•]\s+', '', line_stripped)
            if cleaned:
                current_body_lines.append(cleaned)

    if started:
        save_page(current_page_num, current_title, current_body_lines)

    return pages


def extract_key_points(title: str, body: str) -> List[str]:
    """提取关键要点，过滤复制粘贴残留词"""
    if not body:
        return []
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    kp = []
    for l in lines:
        l = re.sub(r'^[-*•]\s+', '', l)
        if l in ('plain', '复制', 'markdown', 'html'):
            continue
        if len(l) < 8 or l.startswith('```'):
            continue
        if l.startswith('生成') or l.startswith('请生成') or l.startswith('创建'):
            continue
        kp.append(l[:100])
        if len(kp) >= 5:
            break
    return kp


def normalize_outline_fields(outline: Dict, index: int) -> Dict:
    """确保每个outline包含所有必要字段

    LLM返回的字段名可能是：
    - outline_content / title / page_title（标题）
    - part / section（章节类型）
    - page_instruction / instruction（页面提示词）
    - page_number / page（页码）
    """
    if 'page' not in outline:
        outline['page'] = outline.get('page_number', index + 1)


    # 提取真实标题：优先 page_title > title > outline_content
    raw_title = (
        outline.get('page_title')
        or outline.get('title')
        or outline.get('outline_content', '')
        or ''
    ).strip()
    # 如果形如 "第X页" / "第X页：" / 只有页码 → 从 page_instruction 第一句提取
    generic_pattern = re.match(r'^第[一二三四五六七八九十零0-9]+页\s*[:：]?\s*$', raw_title)
    if generic_pattern and outline.get('page_instruction'):
        pi = outline['page_instruction']
        title_candidate = re.split(r'[。！？；,\n]', pi)[0].strip()
        outline['outline_content'] = title_candidate[:40] if title_candidate else f'第{index + 1}页'
        # 如果提取出来的仍只是 "设计..." 类动作描述，则搜索 page_instruction 中的标题型词语
        if outline['outline_content'].startswith('设计') and len(outline['outline_content']) > 6:
            title_match = re.search(r'([^\s]{2,6}页|[^\s]{2,8}概述|[^\s]{2,8}总结|[^\s]{2,8}总览)', pi)
            if title_match:
                outline['outline_content'] = title_match.group(1)[:40]
    elif not outline.get('outline_content'):
        # outline_content 为空或不存在时，用真实标题填充
        outline['outline_content'] = raw_title or f'第{index + 1}页'


    # part 规范化：映射非标准值（summary/overview/achievement/analysis/method/summary/appendix）
    raw_part = (outline.get('part') or outline.get('section') or '').strip().lower()
    part_map = {
        'summary': '总结', 'conclusion': '总结', 'overview': '背景',
        'achievement': '成果', 'result': '成果', 'success': '成果',
        'analysis': '分析', 'diagnosis': '分析',
        'method': '方法', 'approach': '方法', 'strategy': '方法',
        'background': '背景', 'intro': '背景',
        'appendix': '总结', 'appendix': '总结'
    }
    normalized_part = part_map.get(raw_part, outline.get('part', ''))
    if normalized_part not in ('背景', '分析', '方法', '成果', '总结', '概述', '目录'):
        title_for_part = outline.get('page_instruction', '') or outline.get('outline_content', '')
        normalized_part = guess_part(title_for_part)
    outline['part'] = normalized_part

    if 'layout_hint' not in outline:
        outline['layout_hint'] = '两栏'
    if 'page_instruction' not in outline or not outline['page_instruction']:
        outline['page_instruction'] = outline.get('instruction') or outline.get('outline_content', f'第{index + 1}页')
    if 'key_points' not in outline:
        outline['key_points'] = []
    return outline


def _cn2int(text: str) -> int:
    """Convert Chinese numerals (一 二 ... 九 十 零) or Arabic digits to int."""
    text = text.strip()
    cn_map = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,'零':0}
    if text.isdigit():
        return int(text)
    if text in cn_map:
        return cn_map[text]
    # Handle "十二" = 12, "二十五" = 25 etc.
    if '十' in text:
        parts = text.split('十', 1)
        tens = cn_map.get(parts[0], 1) * 10
        ones = cn_map.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
        return tens + ones
    return 0


def _parse_page_numbered_direct(theme_text: str) -> List[Dict]:
    """
    Directly parse "第X页：标题\n内容..." format without LLM.
    Each "第X页" section becomes one page with:
      - outline_content: the page title (after "第X页：")
      - page_instruction: ALL content under that page (AI generation basis)
      - part: guessed from title
    """
    text = theme_text.strip()

    # Split into page sections using "第X页：" as delimiter
    # Pattern matches at line start:
    #   第(1|一|二...|九|十|零)页：
    # This splits the text into [before_first_page, page1_content, page2_content, ...]
    page_delimiter = r'\n(?=第[一二三四五六七八九十零0-9]+\s*页\s*[:：])'
    sections = re.split(page_delimiter, text)

    outlines = []
    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Extract: "第X页：标题" at the start of section
        m = re.match(r'^第([一二三四五六七八九十零0-9]+)\s*页\s*[:：]\s*(.*)', section)
        if not m:
            continue

        page_num = _cn2int(m.group(1))
        page_title = m.group(2).strip()

        # Everything after the first line is the page body (AI generation basis)
        body_start = m.end()
        page_body = section[body_start:].strip()

        # Ensure we always have a useful outline_content
        if not page_title or len(page_title) < 2:
            # Try to extract from first line of body
            first_body_line = page_body.split('\n')[0].strip() if page_body else ''
            if first_body_line:
                page_title = first_body_line[:60]
            else:
                page_title = f'第{page_num}页'

        outlines.append({
            'page': page_num,
            'part': guess_part(page_title),
            'outline_content': page_title[:80],
            'page_instruction': page_body if page_body else page_title,
        })

    return outlines


def analyze_theme_stream(theme_text: str, text_provider=None) -> Generator[Dict, None, None]:
    """
    流式生成大纲。每次yield一个SSE事件。
    当检测到"第X页"结构化格式时，直接解析无需LLM调用。
    """
    try:
        yield {'type': 'started', 'message': '正在理解主题结构...'}

        # ---- Direct parsing for "第X页" structured format ----
        if re.search(r'第[一二三四五六七八九十零0-9]+\s*页', theme_text):
            outlines = _parse_page_numbered_direct(theme_text)
            if outlines:
                yield {'type': 'analyzing', 'message': f'检测到结构化格式，已识别 {len(outlines)} 个页面', 'progress': 50}
                outlines = [normalize_outline_fields(o, i) for i, o in enumerate(outlines)]
                yield {'type': 'analyzing', 'message': '大纲解析完成', 'progress': 100}
                for i, outline in enumerate(outlines):
                    yield {'type': 'outline', 'index': i, 'data': outline}
                yield {'type': 'complete', 'outlines': outlines, 'total': len(outlines)}
                return

        # ---- LLM-based analysis for other formats ----

        # 【核心改进】始终调用LLM理解输入，再生成结构
        if text_provider is None:
            from services.ai_providers import get_text_provider
            text_provider = get_text_provider()

        # 清理残留词后再发LLM
        theme_text_clean = clean_theme_text(theme_text)
        system_prompt, user_prompt = build_analysis_prompt(theme_text_clean)
        yield {'type': 'analyzing', 'message': '正在分析页面结构...', 'progress': 20}

        # 调用LLM获取完整结构（流式拼接）
        full_response = ''
        for chunk in text_provider.generate_text_stream(user_prompt):
            full_response += chunk
            yield {'type': 'analyzing', 'message': '正在理解内容...', 'progress': 50}

        yield {'type': 'analyzing', 'message': '正在解析大纲...', 'progress': 80}

        outlines = parse_llm_json_response(full_response)
        if not outlines:
            yield {'type': 'error', 'message': 'AI未返回有效大纲，请尝试更详细的主题描述'}
            return

        # 规范化每个outline的字段
        outlines = [normalize_outline_fields(o, i) for i, o in enumerate(outlines)]

        for i, outline in enumerate(outlines):
            yield {'type': 'outline', 'index': i, 'data': outline}

        yield {'type': 'complete', 'outlines': outlines, 'total': len(outlines)}

    except Exception as e:
        logger.exception(f"[ThemeAnalysis] Stream failed: {e}")
        yield {'type': 'error', 'message': str(e)}


def analyze_theme_sync(theme_text: str, text_provider=None) -> tuple[List[Dict], Optional[str]]:
    """同步版本的大纲分析"""
    try:
        if text_provider is None:
            from services.ai_providers import get_text_provider
            text_provider = get_text_provider()

        system_prompt, user_prompt = build_analysis_prompt(theme_text)
        response = text_provider.generate_text(user_prompt)

        outlines = parse_llm_json_response(response)
        if not outlines:
            return [], 'AI未返回有效大纲'

        outlines = [normalize_outline_fields(o, i) for i, o in enumerate(outlines)]
        return outlines, None

    except Exception as e:
        logger.exception(f"[ThemeAnalysis] Sync failed: {e}")
        return [], str(e)