"""
Chat Controller - Multi-turn AI conversation for PPT outline generation
v0.6 Feature 2: AI 人机对话生成 PPT 大纲提示词
"""
import logging
from flask import Blueprint, request, Response, current_app
import json

from services.ai_providers import get_text_provider

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')


SYSTEM_PROMPT = """你是一个PPT大纲助手，名字叫PPT小助手。

## 你的职责
根据用户的描述，生成或优化PPT大纲结构。用户可能会：
- 描述一个PPT主题，让你生成大纲
- 追问修改某个页面
- 确认大纲完成

## 大纲格式
你返回的每页大纲必须包含：
- part: 章节类型（背景/分析/方法/成果/总结/概述）
- outline_content: 页面标题（简洁，20字以内）
- page_instruction: 页面生成提示词（详细描述该页要展示的内容、布局、风格）
- layout_hint: 推荐布局（两栏/单栏/图右文左/图上文下）

## 输出规则
1. 如果用户描述了一个PPT主题 → 生成5-8页结构化大纲
2. 如果用户要求修改某页 → 调整对应页面，保留其他页面
3. 如果用户说"确定了"或"可以了" → 补充完整 page_instruction 后输出 "FINAL_CONFIRM"
4. 你只能输出JSON数组，不要输出其他内容
5. page_instruction 要非常详细，包含：核心主题、关键内容、视觉设计建议、配色提示

## 示例
用户输入：帮我做一个关于电网智能化的汇报
你输出：
```json
[
  {"part":"背景","outline_content":"项目背景与目标","page_instruction":"介绍电网智能化的宏观背景，国家双碳目标、能源转型政策，电网作为关键基础设施的地位。布局建议：左侧政策图标，右侧核心数据。配色：蓝色系。","layout_hint":"两栏"},
  {"part":"分析","outline_content":"现状分析","page_instruction":"分析当前电网面临的主要挑战：新能源消纳压力大、设备老旧、运维效率低。展示关键数据和痛点。布局建议：三栏卡片式。配色：蓝色系。","layout_hint":"三栏"}
]
```"""


CHAT_HISTORY_MAX_TURNS = 10  # 每 turn = 2 条消息 (user + assistant), 保留最近 10 轮 = 20 条


def _build_messages(theme_text: str, history: list = None) -> list:
    """
    Build messages for the LLM, incorporating conversation history.
    Auto-truncates when history exceeds CHAT_HISTORY_MAX_TURNS turns.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        recent = list(history)
        max_messages = CHAT_HISTORY_MAX_TURNS * 2  # user + assistant per turn
        if len(recent) > max_messages:
            # Keep most recent, add truncation notice
            dropped = len(recent) - max_messages
            recent = recent[-max_messages:]
            messages.append({
                "role": "system",
                "content": f"[注意：早期 {dropped} 条对话已省略，以下是最近的 {max_messages} 条对话]"
            })
            logger.info(f"[Chat] History truncated: dropped {dropped} messages, kept {max_messages}")
        for h in recent:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

    messages.append({"role": "user", "content": theme_text})
    return messages


def _generate_outline_events(messages: list, text_provider=None) -> list:
    """
    Call LLM with conversation history and parse outline events.
    Returns list of outline dicts.
    """
    if text_provider is None:
        text_provider = get_text_provider(model='MiniMax-M2.7')

    response_text = text_provider.generate_text_messages(
        messages=messages,
        thinking_budget=0,
    )

    # Strip think tags
    response_text = response_text.strip()

    # Check for FINAL_CONFIRM
    final_confirm = "FINAL_CONFIRM" in response_text
    response_text = response_text.replace("FINAL_CONFIRM", "").strip()

    # Try to find JSON array in response
    json_match = None
    for pattern in [r'\[[\s\S]+\]', r'\{[\s\S]*"part"[\s\S]*\}']:
        m = _find_json_pattern(response_text, pattern)
        if m:
            json_match = m
            break

    outlines = []
    if json_match:
        try:
            data = json.loads(json_match)
            if isinstance(data, list):
                outlines = data
            elif isinstance(data, dict):
                outlines = [data]
        except json.JSONDecodeError:
            pass

    # Normalize fields
    normalized = []
    for i, o in enumerate(outlines):
        if 'page' not in o:
            o['page'] = i + 1
        if 'outline_content' not in o and 'title' in o:
            o['outline_content'] = o['title']
        if 'page_instruction' not in o and 'instruction' in o:
            o['page_instruction'] = o['instruction']
        if not o.get('page_instruction'):
            o['page_instruction'] = o.get('outline_content', f'第{i+1}页')
        if not o.get('part'):
            o['part'] = '概述'
        normalized.append(o)

    return normalized, final_confirm


def _find_json_pattern(text: str, pattern: str):
    """Find JSON matching the given regex pattern in text."""
    import re
    match = re.search(pattern, text)
    return match.group(0) if match else None


@chat_bp.route('/generate-outline', methods=['POST'])
def generate_outline():
    """
    POST /api/chat/generate-outline
    Multi-turn AI conversation to generate PPT outlines.

    Body: {
        "messages": [
            {"role": "user", "content": "帮我做电网智能化的PPT"},
            {"role": "assistant", "content": "好的，这是大纲..."},
            {"role": "user", "content": "第一页改成研究背景"}
        ],
        "final": false  // true = user confirmed, return final outlines
    }
    """
    try:
        data = request.get_json() or {}
        messages = data.get('messages', [])
        is_final = data.get('final', False)

        if not messages:
            return {'success': False, 'error': 'messages is required'}, 400

        # Build LLM messages
        last_user_msg = messages[-1]['content'] if messages else ''
        llm_messages = _build_messages(last_user_msg, messages[:-1])

        # Get text provider
        from models.settings import Settings
        settings = Settings.query.first()
        provider_format = settings.ai_provider_format if settings else 'minimax'
        text_provider = get_text_provider(model=settings.text_model if settings and settings.text_model else 'MiniMax-M2.7')

        def generate():
            try:
                yield 'data: ' + json.dumps({'type': 'started', 'message': '正在生成大纲...'}) + '\n\n'

                outlines, final_confirm = _generate_outline_events(llm_messages, text_provider)

                if final_confirm or is_final:
                    yield 'data: ' + json.dumps({'type': 'complete', 'outlines': outlines, 'total': len(outlines)}) + '\n\n'
                    return

                for i, outline in enumerate(outlines):
                    yield 'data: ' + json.dumps({'type': 'outline', 'index': i, 'data': outline}) + '\n\n'

                yield 'data: ' + json.dumps({'type': 'complete', 'outlines': outlines, 'total': len(outlines)}) + '\n\n'

            except Exception as e:
                logger.error(f"[Chat] Generate outline failed: {e}")
                yield 'data: ' + json.dumps({'type': 'error', 'message': str(e)}) + '\n\n'

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            }
        )

    except Exception as e:
        logger.error(f"[Chat] generate-outline endpoint error: {e}")
        return {'success': False, 'error': str(e)}, 500