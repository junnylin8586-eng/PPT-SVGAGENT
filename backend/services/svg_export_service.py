"""
SVG Export Service - Path D: SVG → DrawingML → PPTX

Wraps ppt-master engine for programmatic invocation from Flask.
Phase 1.5: Minimal end-to-end SVG→PPTX pipeline test.
"""
import io
import os
import re
import sys
import logging
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Add ppt-master engine to path
_PPT_MASTER_ENGINE = Path(__file__).parent.parent / 'ppt_master_engine' / 'scripts'
if str(_PPT_MASTER_ENGINE) not in sys.path:
    sys.path.insert(0, str(_PPT_MASTER_ENGINE))


def get_engine_path() -> Path:
    return _PPT_MASTER_ENGINE


def _validate_svg_xml(svg_path: Path) -> tuple[bool, str]:
    """Validate SVG is well-formed XML. Returns (is_valid, error_msg)."""
    try:
        import xml.etree.ElementTree as ET
        content = svg_path.read_text(encoding='utf-8')
        # Reject truncated SVG (missing </svg> closing tag — AI preamble or cut-off response)
        if '</svg>' not in content:
            return False, 'missing closing </svg> tag'
        ET.parse(str(svg_path))
        return True, ''
    except Exception as e:
        return False, str(e)


def _sanitize_svg_for_export(svg_path: Path, verbose: bool = False) -> Path:
    """
    Create a sanitized in-memory copy of an SVG for safe export.

    Fixes applied (on a temp copy, never mutates the original):
    1. Strip AI commentary/preamble before <svg> tag
    2. Fix bare `&` not part of valid XML entities
    3. Strip invalid `]]>` artifacts
    4. Ensure proper XML namespace declarations
    5. Wrap bare text in CDATA where safe

    Returns:
        Path to a temp-file copy of the sanitized SVG.
        Caller is responsible for cleanup (the temp file is in the system
        temp dir and will be cleaned on next reboot).
    """
    import tempfile
    import re

    content = svg_path.read_text(encoding='utf-8')
    original_size = len(content)

    # 1. Locate the first <svg tag and discard everything before it
    svg_start = content.find('<svg')
    if svg_start == -1:
        # File has no <svg> tag — likely a truncated AI response
        raise ValueError(f'No <svg> tag found in {svg_path.name}')
    if svg_start > 0:
        content = content[svg_start:]

    # 2. Locate the matching </svg> closing tag (find the LAST one)
    svg_close = content.rfind('</svg>')
    if svg_close == -1:
        raise ValueError(f'Missing </svg> closing tag in {svg_path.name}')
    content = content[:svg_close + len('</svg>')]

    # 3. Strip XML comments (bare & inside comments are valid XML but
    #    confuse entity-fix regexps; extract-and-restore pattern)
    comments: list[str] = []
    def _save_comment(m):
        comments.append(m.group(0))
        return f'__COMMENT_{len(comments) - 1}__'
    content = re.sub(r'<!--[\s\S]*?-->', _save_comment, content)

    # 4. Fix bare & not part of valid XML entity references
    #    Valid: &amp; &lt; &gt; &quot; &apos; &#NN; &#xNN;
    content = re.sub(r'&(?![a-zA-Z#][a-zA-Z0-9#]*;)', '&amp;', content)

    # 5. Strip invalid ]]> artifacts (XML reserved, invalid outside CDATA)
    content = content.replace(']]>', ']]&gt;')

    # 6. Deduplicate attributes — AI sometimes emits duplicate attrs like x="0" x="60"
    #    XML spec forbids duplicate attributes on the same element.
    def _dedup_attrs(match):
        tag_body = match.group(0)
        attr_pattern = re.compile(r'(\s)(\w[\w:-]*)(\s*=\s*["\'][^"\']*["\'])', re.DOTALL)
        seen_attrs = set()
        result = []
        last_end = 0
        for m in attr_pattern.finditer(tag_body):
            name = m.group(2)
            if name.lower() in seen_attrs:
                # Advance past this duplicate so final append skips it
                last_end = m.end()
                continue
            seen_attrs.add(name.lower())
            result.append(tag_body[last_end:m.start()])
            result.append(m.group(0))
            last_end = m.end()
        result.append(tag_body[last_end:])
        return ''.join(result)

    content = re.sub(r'<(?!\?|!--|!\[CDATA)[^>]+>', _dedup_attrs, content)

    # 7. Restore comments
    for i, cmt in enumerate(comments):
        content = content.replace(f'__COMMENT_{i}__', cmt)

    # 8. Validate the result is well-formed XML
    parse_err = None
    try:
        ET.parse(io.StringIO(content))
    except Exception as e1:
        parse_err = str(e1)

    if parse_err:
        logger.warning(
            f'[SVG Export] {svg_path.name} still invalid after sanitize: {parse_err}. '
            'Trying aggressive fix...'
        )
        lines = content.split('\n')
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if stripped and not (stripped.startswith('<') or stripped.startswith('</')):
                continue
            line = re.sub(r'<(?!\?|!--|!\[CDATA)[^>]+>', _dedup_attrs, line)
            cleaned.append(line)
        content = '\n'.join(cleaned)
        try:
            ET.parse(io.StringIO(content))
        except Exception as e2:
            raise ValueError(
                f'Cannot fix {svg_path.name}: SVG is irreparably malformed: {e2}'
            )

    if verbose and len(content) != original_size:
        delta = len(content) - original_size
        logger.info(
            f'[SVG Export] Sanitized {svg_path.name}: '
            f'{original_size} → {len(content)} bytes ({"+" if delta > 0 else ""}{delta})'
        )

    # Write sanitized content to a temp file (won't overwrite original)
    fd, tmp_path = tempfile.mkstemp(suffix='.svg', prefix='sanitized_')
    os.close(fd)
    Path(tmp_path).write_text(content, encoding='utf-8')
    return Path(tmp_path)


def create_pptx_from_svgs(
    svg_files: list[Path],
    output_path: Path,
    canvas_format: str = 'ppt169',
    use_native_shapes: bool = True,
    transition: str = 'fade',
    transition_duration: float = 0.5,
    verbose: bool = True,
) -> dict:
    """
    Create PPTX from SVG files using ppt-master engine.

    Args:
        svg_files: List of SVG file paths (ordered, one per slide).
        output_path: Output PPTX file path.
        canvas_format: Canvas format key (ppt169 | ppt43 | ...).
        use_native_shapes: If True → Path D (DrawingML, fully editable).
                           If False → SVG embedded as image.
        transition: Transition effect (fade | none | ...).
        transition_duration: Transition duration in seconds.
        verbose: Print progress info.

    Returns:
        dict with keys:
            success (bool): True if PPTX was created.
            skipped (list[int]): 1-based slide indices that were skipped.
            sanitize_failures (list[str]): Names of files that failed sanitization.
            native_fallback (bool): True if image fallback was used.
            error (str or None): Error message if success is False.
    """
    from svg_to_pptx import create_pptx_with_native_svg

    result = {
        'success': False,
        'skipped': [],
        'sanitize_failures': [],
        'native_fallback': False,
        'error': None,
    }

    if not svg_files:
        result['error'] = 'No SVG files provided'
        logger.error(f'[SVG Export] {result["error"]}')
        return result

    # Validate and sanitize all SVG files before processing.
    # Gracefully skip irreparable files — do NOT fail the entire export.
    sanitized_svgs: list[Path] = []
    skipped_indices: list[int] = []
    for idx, f in enumerate(svg_files):
        if not f.exists():
            logger.warning(f'[SVG Export] SVG file not found, skipping: {f}')
            skipped_indices.append(idx + 1)
            continue
        try:
            sanitized = _sanitize_svg_for_export(f, verbose)
            sanitized_svgs.append(sanitized)
        except Exception as e:
            logger.warning(
                f'[SVG Export] Skipping {f.name}: sanitization failed ({e}). '
                'Export will continue without this slide.'
            )
            result['sanitize_failures'].append(f.name)
            skipped_indices.append(idx + 1)

    result['skipped'] = skipped_indices

    if not sanitized_svgs:
        result['error'] = 'All SVG files failed sanitization'
        logger.error(f'[SVG Export] {result["error"]}')
        return result

    # Use sanitized copies for the entire pipeline
    svg_files = sanitized_svgs

    try:
        if verbose:
            total_expected = len(svg_files) + len(skipped_indices)
            logger.info(
                f'[SVG Export] Creating PPTX with {len(svg_files)}/{total_expected} slides '
                f'({len(skipped_indices)} skipped)...'
            )
            logger.info(f'[SVG Export] Output: {output_path}')
            logger.info(f'[SVG Export] Canvas: {canvas_format}, Native shapes: {use_native_shapes}')

        # Pre-validate: test each SVG for native conversion compatibility
        bad_slides = []
        if use_native_shapes:
            for idx, svg_path in enumerate(svg_files):
                try:
                    _pre_check_svg_native(svg_path, idx + 1)
                except Exception as pre_err:
                    logger.warning(
                        f'[SVG Export] Slide {idx+1} ({svg_path.name}) native check failed: {pre_err}. '
                        'Will use image fallback for this slide.'
                    )
                    bad_slides.append(idx)

        svg_path_objects = [f if isinstance(f, Path) else Path(f) for f in svg_files]

        if not bad_slides:
            success = create_pptx_with_native_svg(
                svg_files=svg_path_objects,
                output_path=output_path if isinstance(output_path, Path) else Path(output_path),
                canvas_format=canvas_format,
                verbose=verbose,
                use_compat_mode=True,
                use_native_shapes=use_native_shapes,
                transition=transition,
                transition_duration=transition_duration,
            )
        else:
            logger.info(f'[SVG Export] {len(bad_slides)} slide(s) need image fallback, using compat mode')
            result['native_fallback'] = True
            success = create_pptx_with_native_svg(
                svg_files=svg_path_objects,
                output_path=output_path if isinstance(output_path, Path) else Path(output_path),
                canvas_format=canvas_format,
                verbose=verbose,
                use_compat_mode=True,
                use_native_shapes=False,
                transition=transition,
                transition_duration=transition_duration,
            )

        if success:
            logger.info(f'[SVG Export] PPTX created: {output_path}')
            result['success'] = True
        else:
            result['error'] = 'create_pptx_with_native_svg returned False'
            logger.error(f'[SVG Export] {result["error"]}')

        return result

    except Exception as e:
        result['error'] = str(e)
        logger.error(f'[SVG Export] Failed: {e}')
        import traceback
        traceback.print_exc()
        return result

    finally:
        # Clean up sanitized temp SVGs to avoid disk accumulation
        for f in sanitized_svgs:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass


def _pre_check_svg_native(svg_path: Path, slide_num: int = 1) -> None:
    """
    Test whether an SVG can be converted to native DrawingML shapes.
    Raises exception if conversion would fail.
    """
    from svg_to_pptx.drawingml_converter import convert_svg_to_slide_shapes
    convert_svg_to_slide_shapes(svg_path, slide_num=slide_num, verbose=False)


def _try_fix_malformed_svg(svg_path: Path) -> bool:
    """
    Attempt to fix malformed SVG by:
    1. Stripping AI commentary/preamble (leading text before <svg tag)
    2. Handling truncated SVGs (missing </svg> — replaced with fallback)

    Returns True if file was fixed, False otherwise.
    """
    try:
        content = svg_path.read_text(encoding='utf-8')
        original = content

        # Case 1: File has <svg> tag somewhere (preamble stripped, or clean start)
        # but no closing </svg> → AI gave partial response, replace with fallback
        if '</svg>' not in content:
            import re
            # Extract page index from filename like "slide_03.svg"
            m = re.search(r'slide_(\d+)\.svg', svg_path.name)
            page_index = int(m.group(1)) if m else 1

            # Try to find an outline in the file itself (AI wrote it there before crashing)
            # Look for Chinese text patterns that might be outline content
            outline_match = re.search(r'["\']([^"\']{10,50})["\']\s*$', content, re.MULTILINE)
            fallback_content = outline_match.group(1) if outline_match else ''

            fallback_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#003371"/>
  <text x="640" y="320" font-family="system-ui, sans-serif" font-size="52"
        fill="white" text-anchor="middle" font-weight="bold">第 {page_index} 页</text>
  <text x="640" y="400" font-family="system-ui, sans-serif" font-size="24"
        fill="#AACCEE" text-anchor="middle">{fallback_content or '内容生成中...'}</text>
  <rect x="560" y="440" width="160" height="6" rx="3" fill="#00875A"/>
</svg>'''
            svg_path.write_text(fallback_svg, encoding='utf-8')
            logger.info(f'[SVG Export] Replaced truncated SVG with fallback: {svg_path.name}')
            return True

        # Case 2: File has both <svg> and </svg> but is malformed → strip preamble
        import re
        svg_start_match = re.search(r'<svg\s', content)
        if not svg_start_match:
            return False

        svg_start = svg_start_match.start()
        if svg_start > 0:
            content = content[svg_start:]
            logger.info(f'[SVG Export] Stripped {svg_start} bytes of preamble from {svg_path.name}')

        # Strip XML comments <!-- ... -->
        content = re.sub(r'<!--[\s\S]*?-->', '', content)

        # Remove ]]> (XML reserved, invalid outside CDATA — AI artifact)
        content = content.replace(']]>', '')

        # Fix bare & not followed by valid entity
        content = re.sub(r'&(?![a-zA-Z#][a-zA-Z0-9#]*;)', '&amp;', content)

        if content != original:
            svg_path.write_text(content, encoding='utf-8')
            logger.info(f'[SVG Export] Fixed malformed SVG: {svg_path.name}')
            return True

        return False
    except Exception as e:
        logger.warning(f'[SVG Export] Could not fix SVG {svg_path.name}: {e}')
        return False


def quality_check_svg(svg_file: Path) -> dict:
    """
    Run svg_quality_checker on a single SVG file.

    Returns:
        dict with keys: passed (bool), errors (list), warnings (list)
    """
    from svg_quality_checker import SVGQualityChecker

    checker = SVGQualityChecker()
    result = checker.check_file(str(svg_file))

    return {
        'passed': result['passed'],
        'errors': result['errors'],
        'warnings': result['warnings'],
        'info': result.get('info', {}),
    }


def finalize_svg_files(project_svg_dir: Path, output_dir: Path) -> bool:
    """
    Run finalize_svg.py on all SVG files in a directory.

    Args:
        project_svg_dir: Directory containing svg_output/ (raw SVGs).
        output_dir: Directory to write svg_final/ to.

    Returns:
        True if successful.
    """
    try:
        from finalize_svg import finalize_project

        result = finalize_project(
            project_dir=project_svg_dir,
            options={
                'embed_icons': True,
                'crop_images': True,
                'fix_aspect': True,
                'embed_images': True,
                'flatten_text': True,
                'fix_rounded': True,
            },
            dry_run=False,
            quiet=False,
        )
        return result
    except Exception as e:
        logger.error(f'[SVG Export] finalize_svg failed: {e}')
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# Phase 1.5 Minimal Test
# =============================================================================

def test_minimal_path_d():
    """
    Phase 1.5 validation: Create a minimal SVG -> Path D PPTX.
    Uses a persistent temp dir so we can inspect the output.
    """
    print('=' * 60)
    print('Phase 1.5: Minimal Path D Test')
    print('=' * 60)

    test_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#003371"/>
  <text x="640" y="320" font-family="system-ui, sans-serif" font-size="60"
        fill="white" text-anchor="middle" font-weight="bold">PPT Agent Test</text>
  <text x="640" y="400" font-family="system-ui, sans-serif" font-size="28"
        fill="#AACCEE" text-anchor="middle">Path D: Native DrawingML Export</text>
  <rect x="560" y="440" width="160" height="6" rx="3" fill="#00875A"/>
</svg>'''

    tmpdir = Path(tempfile.gettempdir()) / 'ppt_agent_phase15_test'
    tmpdir.mkdir(exist_ok=True)
    svg_path = tmpdir / 'slide_01_test.svg'
    pptx_path = tmpdir / 'output_test.pptx'

    svg_path.write_text(test_svg, encoding='utf-8')
    print(f'[1/3] SVG written: {svg_path}')

    print('[2/3] Running quality check...')
    qc_result = quality_check_svg(svg_path)
    print(f'       Passed: {qc_result["passed"]}')
    if qc_result['errors']:
        print(f'       Errors: {qc_result["errors"]}')
    if qc_result['warnings']:
        print(f'       Warnings: {qc_result["warnings"]}')

    print('[3/3] Creating PPTX via Path D...')
    success = create_pptx_from_svgs(
        svg_files=[svg_path],
        output_path=pptx_path,
        canvas_format='ppt169',
        use_native_shapes=True,
        transition='fade',
        verbose=True,
    )

    if success and pptx_path.exists():
        size_kb = pptx_path.stat().st_size / 1024
        print(f'\n[SUCCESS] PPTX created ({size_kb:.1f} KB)')
        print(f'   Path: {pptx_path}')

        # Quick ZIP structure verification
        import zipfile, re
        with zipfile.ZipFile(str(pptx_path)) as z:
            names = z.namelist()
            slide_xml = z.read('ppt/slides/slide1.xml').decode('utf-8')
            sp_count = len(re.findall('<p:sp>', slide_xml))
            pic_count = len(re.findall('<p:pic>', slide_xml))
            texts = re.findall(r'<a:t>([^<]+)</a:t>', slide_xml)
            print(f'   ZIP entries: {len(names)}')
            print(f'   p:sp shapes: {sp_count}')
            print(f'   p:pic images: {pic_count}')
            print(f'   Text elements: {texts}')
        return True
    else:
        print('\n[FAILED] PPTX not created')
        return False


if __name__ == '__main__':
    success = test_minimal_path_d()
    sys.exit(0 if success else 1)
