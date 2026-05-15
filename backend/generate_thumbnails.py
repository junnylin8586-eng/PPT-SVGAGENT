"""
Generate template thumbnail PNGs using PIL (no external dependencies beyond Pillow).
Run: .venv\Scripts\python.exe generate_thumbnails.py
"""
from PIL import Image, ImageDraw, ImageFont
import os

# Template definitions: (id, name_cn, bg_color, accent_color, title_en, subtitle, layout_style)
TEMPLATES = [
    ('government_blue',    '重点项目汇报',  '#003371', '#00875A', 'Key Project\nReport',           '2024 Annual Summary',      'dark_header'),
    ('government_red',     '政府汇报',       '#8B0000', '#FF6347', 'Government\nReport',            'Policy & Implementation',   'dark_header'),
    ('anthropic',          'AI科技发布',    '#0F172A', '#10B981', 'AI Product\nLaunch',            'Next Generation',           'dark_header'),
    ('ai_ops',             '电信AI运营',     '#003371', '#00875A', 'AI Ops\nArchitecture',           'Intelligent Operations',    'dark_header'),
    ('google_style',       '年度工作汇报',   '#FFFFFF', '#4285F4', 'Annual\nReport',                '2024 Key Metrics',          'light_header'),
    ('academic_defense',   '学术答辩',       '#1A365D', '#E2E8F0', 'Thesis\nDefense',               'Academic Presentation',     'dark_header'),
    ('medical_university', '医学学术',       '#002855', '#00A99D', 'Medical\nResearch',             'Clinical Study Report',     'dark_header'),
    ('pixel_retro',        '复古极客',       '#1a1a2e', '#00FF41', '8-BIT\nTECH',                  'Retro Computing',           'neon_header'),
    ('psychology_attachment', '心理培训',    '#E8F5E9', '#2E7D32', 'Psychology\nWorkshop',          'Professional Training',     'light_header'),
    ('china_telecom_template', '政企数字化', '#003087', '#00A9E0', 'Digital\nTransformation',       'Enterprise Solutions',      'dark_header'),
    ('中国电建_常规',      '电建常规汇报',   '#003066', '#E8B04B', 'Engineering\nReport',            'PowerChina | 2024',         'dark_header'),
    ('中国电建_现代',      '电建现代汇报',   '#0D1B2A', '#00C9A7', 'Smart\nEngineering',            'Digital Construction 2024',  'dark_header'),
    ('中汽研_商务',        '中汽研商务',     '#002B5C', '#C9A84C', 'Product\nCertification',        'CATARC | Quality Assurance','dark_header'),
    ('中汽研_常规',        '中汽研常规',     '#003580', '#4A90D9', 'Technical\nReport',             'CATARC | Standards',        'dark_header'),
    ('中汽研_现代',        '中汽研现代',     '#0A1628', '#00E5FF', 'Future\nMobility',              'Strategic Vision 2030',    'neon_header'),
    ('招商银行',           '招商银行',       '#8B0000', '#FFD700', 'Transaction\nBanking',          'CMB | Enterprise Finance',  'dark_header'),
    ('重庆大学',           '重庆大学',       '#B31942', '#FFD700', 'Academic\nResearch',            'Chongqing University',      'dark_header'),
]

W, H = 400, 225  # 16:9


def hex_to_rgb(hex_str):
    h = hex_str.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def load_font(size):
    """Try to load Noto Sans SC, fall back to default."""
    font_paths = [
        'C:/Windows/Fonts/NotoSansSC-Regular.otf',
        'C:/Windows/Fonts/seguisym.ttf',
        'C:/Windows/Fonts/consola.ttf',
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_thumbnail(template_id, name_cn, bg_hex, accent_hex, title_en, subtitle, style, out_path):
    bg = hex_to_rgb(bg_hex)
    accent = hex_to_rgb(accent_hex)
    is_dark = bg[0] + bg[1] + bg[2] < 384  # roughly

    img = Image.new('RGB', (W, H), bg)
    draw = ImageDraw.Draw(img)

    fn_title = load_font(18)
    fn_sub = load_font(10)
    fn_bullet = load_font(9)
    fn_tag = load_font(8)

    if style == 'dark_header':
        # Top: dark accent header bar
        draw.rectangle([(0, 0), (W, 3)], fill=accent)
        # Title area in upper portion
        title_y = 28
        # Small tag
        draw.text((16, 10), name_cn, font=fn_tag, fill=(accent[0], accent[1], accent[2]))
        # Main title (EN)
        draw.text((16, title_y), title_en.replace('\n', ' '), font=fn_title, fill=(255, 255, 255))
        # Subtitle
        sub_y = title_y + 26
        draw.text((16, sub_y), subtitle, font=fn_sub, fill=(170, 204, 238))
        # Divider line
        draw.rectangle([(16, sub_y + 18), (80, sub_y + 19)], fill=accent)
        # Content preview lines
        content_y = sub_y + 30
        lines = [
            '01  项目背景与目标',
            '02  实施方案与进展',
            '03  成果展示与数据',
            '04  后续规划与建议',
        ]
        for i, line in enumerate(lines):
            draw.text((16, content_y + i * 16), line, font=fn_bullet,
                      fill=(200, 220, 240) if is_dark else (80, 80, 80))
        # Bottom gradient strip
        draw.rectangle([(0, H - 24), (W, H)], fill=tuple(int(c * 0.6) for c in bg))

    elif style == 'light_header':
        # White/light style: colored accent on left
        draw.rectangle([(0, 0), (6, H)], fill=accent)
        draw.rectangle([(0, 0), (W, 4)], fill=accent)
        # Title
        draw.text((20, 24), name_cn, font=fn_tag, fill=accent)
        draw.text((20, 38), title_en.replace('\n', ' '), font=fn_title, fill=(40, 40, 40))
        draw.text((20, 62), subtitle, font=fn_sub, fill=(120, 120, 120))
        draw.rectangle([(20, 80), (60, 81)], fill=accent)
        # Content lines
        content_y = 92
        lines = ['01  Revenue & Growth', '02  User Metrics', '03  Product Launch']
        for i, line in enumerate(lines):
            draw.text((20, content_y + i * 16), line, font=fn_bullet, fill=(80, 80, 80))
        draw.rectangle([(0, H - 22), (W, H)], fill=(240, 242, 245))
        draw.text((20, H - 16), name_cn, font=fn_tag, fill=(160, 160, 160))

    elif style == 'neon_header':
        # Dark with neon accent (cyberpunk style)
        draw.rectangle([(0, 0), (W, 3)], fill=accent)
        draw.rectangle([(0, 0), (4, H)], fill=accent)
        # Glowing text effect (draw twice with offset for glow)
        draw.text((18, 26), title_en.replace('\n', ' '), font=fn_title, fill=(10, 20, 30))
        draw.text((16, 24), title_en.replace('\n', ' '), font=fn_title, fill=accent)
        draw.text((16, 56), subtitle, font=fn_sub, fill=(100, 200, 150))
        draw.rectangle([(16, 76), (50, 77)], fill=accent)
        content_y = 86
        lines = ['>>  Algorithms', '>>  Systems', '>>  Code Review']
        for i, line in enumerate(lines):
            draw.text((16, content_y + i * 16), line, font=fn_bullet, fill=accent)
        draw.rectangle([(0, H - 20), (W, H)], fill=(8, 8, 20))
        draw.text((16, H - 14), f'[{name_cn}]', font=fn_tag, fill=(60, 60, 100))

    img.save(out_path, 'PNG')


def main():
    out_dir = r'D:\AI\ppt-agent\frontend\public\template_thumbs'
    os.makedirs(out_dir, exist_ok=True)

    for args in TEMPLATES:
        tmpl_id = args[0]
        out_path = os.path.join(out_dir, f'{tmpl_id}.png')
        draw_thumbnail(*args, out_path)
        size_kb = os.path.getsize(out_path) // 1024
        print(f'[OK] {tmpl_id}.png ({size_kb} KB)')

    print(f'\nGenerated {len(TEMPLATES)} thumbnails in:\n  {out_dir}')


if __name__ == '__main__':
    main()