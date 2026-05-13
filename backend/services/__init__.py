# Services package - PPT Agent
# Note: Only import services that exist and are needed for Phase 3+
# ai_service_manager and task_manager are from banana-slides, not yet available

from .svg_export_service import create_pptx_from_svgs
from .ai_generation_service import generate_page_svg, save_svg_for_page
from .svg_render_service import render_svg_file_to_png, render_svg_string_to_png