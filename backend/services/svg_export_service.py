"""
SVG Export Service - Path D: SVG → DrawingML → PPTX

Wraps ppt-master engine for programmatic invocation from Flask.
Phase 1.5: Minimal end-to-end SVG→PPTX pipeline test.
"""
import os
import sys
import logging
import tempfile
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
        ET.parse(str(svg_path))
        return True, ''
    except Exception as e:
        return False, str(e)


def create_pptx_from_svgs(
    svg_files: list[Path],
    output_path: Path,
    canvas_format: str = 'ppt169',
    use_native_shapes: bool = True,
    transition: str = 'fade',
    transition_duration: float = 0.5,
    verbose: bool = True,
) -> bool:
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
        True if successful, False otherwise.
    """
    from svg_to_pptx import create_pptx_with_native_svg

    if not svg_files:
        logger.error('[SVG Export] No SVG files provided')
        return False

    # Validate all SVG files before processing
    invalid_files = []
    for f in svg_files:
        if not f.exists():
            logger.error(f'[SVG Export] SVG file not found: {f}')
            return False
        valid, err = _validate_svg_xml(f)
        if not valid:
            logger.warning(f'[SVG Export] Malformed SVG (will use fallback): {f.name} — {err}')
            invalid_files.append(f)

    # If any SVG is invalid, try to fix it with lxml/html cleanup
    if invalid_files:
        for f in invalid_files:
            _try_fix_malformed_svg(f)

    try:
        if verbose:
            logger.info(f'[SVG Export] Creating PPTX with {len(svg_files)} slides...')
            logger.info(f'[SVG Export] Output: {output_path}')
            logger.info(f'[SVG Export] Canvas: {canvas_format}, Native shapes: {use_native_shapes}')

        # Pass Path objects directly (function expects list[Path])
        svg_path_objects = [f if isinstance(f, Path) else Path(f) for f in svg_files]
        success = create_pptx_with_native_svg(
            svg_files=svg_path_objects,
            output_path=output_path if isinstance(output_path, Path) else Path(output_path),
            canvas_format=canvas_format,
            verbose=verbose,
            use_compat_mode=True,   # PNG fallback for old Office
            use_native_shapes=use_native_shapes,  # True = DrawingML (Path D)
            transition=transition,
            transition_duration=transition_duration,
        )

        if success:
            logger.info(f'[SVG Export] PPTX created: {output_path}')
        else:
            logger.error('[SVG Export] create_pptx_with_native_svg returned False')

        return success

    except Exception as e:
        logger.error(f'[SVG Export] Failed: {e}')
        import traceback
        traceback.print_exc()
        return False


def _try_fix_malformed_svg(svg_path: Path):
    """
    Attempt to fix malformed SVG by:
    1. Reading as text and stripping known bad patterns
    2. Removing unescaped HTML entity issues
    3. Writing back a cleaned version
    """
    try:
        content = svg_path.read_text(encoding='utf-8')
        original = content

        # Strip any <!-- --> HTML comments that might contain -->
        import re
        content = re.sub(r'<!--[\s\S]*?-->', '', content)

        # Fix common issues: bare & not followed by entity/amp;
        # Only fix & that aren't part of valid entities
        content = re.sub(r'&(?![a-zA-Z#][a-zA-Z0-9#]*;)', '&amp;', content)

        # Remove any remaining obvious XML-illegal chars but keep foreignObject HTML
        # Write back only if changed
        if content != original:
            svg_path.write_text(content, encoding='utf-8')
            logger.info(f'[SVG Export] Fixed malformed SVG: {svg_path.name}')
    except Exception as e:
        logger.warning(f'[SVG Export] Could not fix SVG {svg_path.name}: {e}')


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
