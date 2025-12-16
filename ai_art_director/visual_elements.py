# ai_art_director/visual_elements.py
# Refactored Facade v25.7.0 (COMPLETE)

# Core Utils
from .visuals.core import (
    load_font,
    wrap_text_pil,
    paste_safe_logo as _paste_safe_logo,
    create_blurred_image
)

# Effects
from .visuals.effects import (
    apply_random_animation,
    create_pan_zoom_clip
)

# Renderers
from .visuals.slides import (
    render_intro_slide,
    render_glass_news_slide,
    render_sector_slide,
    render_management_slide,
    render_news_slide,
    render_summary_slide,
    render_chart_slide,
    render_cta_slide_grid,
    render_cta_slide_linear,
    render_cta_slide_circular,
    render_cta_slide_diamond
)

print("✅ visual_elements facade loaded.")