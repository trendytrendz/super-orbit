# ai_art_director/visuals/compositor.py
# v27.9.1 - Hook Isolation, Visibility Fixes, Layout Safety

import os
import io
import numpy as np
import cairosvg
from PIL import Image, ImageDraw, ImageFont
from ..config import ASSETS_DIR, ICONS
from .theme_config import THEMES
from . import core
from ..story_runners_refactored.background_manager import BackgroundManager

bg_manager = BackgroundManager()

def get_smart_background_path(ticker, headline, mode, specific_image=None):
    img_path = None
    
    # 1. User Specified Image
    if specific_image:
        candidates = [
            specific_image,
            os.path.join(ASSETS_DIR, "bgImage", specific_image),
            os.path.join(ASSETS_DIR, "custom_news", specific_image),
            os.path.join(ASSETS_DIR, specific_image)
        ]
        for p in candidates:
            if os.path.exists(p):
                img_path = p; break

    # 2. Ticker Match (Auto-Magic)
    if not img_path:
        clean = ticker.replace(".NS", "").replace(".BO", "").strip()
        candidates = [
            os.path.join(ASSETS_DIR, "bgImage", f"{clean}.jpg"),
            os.path.join(ASSETS_DIR, "bgImage", f"{clean}.png"),
            os.path.join(ASSETS_DIR, "bgImage", f"{clean}.jpeg")
        ]
        for p in candidates:
            if os.path.exists(p):
                img_path = p; break
    
    # 3. Pexels Fallback
    if not img_path:
        q = headline if len(headline) > 5 else f"{ticker} news"
        res = bg_manager.fetch_contextual_backgrounds(ticker, q, 1, "portrait", [q])
        if res and res.get('bg_images'): img_path = res['bg_images'][0]

    # 4. Color Fallback
    if not img_path or not os.path.exists(img_path):
        from ..config import TMP_IMG_DIR
        img_path = os.path.join(TMP_IMG_DIR, "fallback_blue.jpg")
        Image.new("RGB", (1080, 1920), "#001f3f").save(img_path)

    return img_path

def draw_text_with_effect(draw, pos, text, font, color, effect):
    x, y = pos
    if effect == "shadow": draw.text((x+4, y+4), text, font=font, fill="black")
    elif effect == "outline":
        for adj in [(-3,-3), (3,3), (-3,3), (3,-3)]: draw.text((x+adj[0], y+adj[1]), text, font=font, fill="black")
    elif effect == "glow":
        for i in range(1,4): draw.text((x+i, y+i), text, font=font, fill="#003300")
    draw.text((x, y), text, font=font, fill=color)

def draw_hero_logo(canvas, icon_name, y_pos=None):
    if not icon_name: return
    W, H = canvas.size; icon_size = 180; badge_size = icon_size + 20
    cx = W // 2; cy = y_pos if y_pos else 300 
    logo_dir = os.path.join(ASSETS_DIR, "Logo")
    paths = [os.path.join(logo_dir, f"{icon_name}.png"), os.path.join(logo_dir, f"{icon_name}.jpg"), os.path.join(logo_dir, icon_name)]
    found_path = next((p for p in paths if os.path.exists(p)), None)
    if found_path:
        try:
            src = Image.open(found_path).convert("RGBA")
            padding = 30; target_w = icon_size - padding; target_h = icon_size - padding
            src.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
            badge = Image.new("RGBA", (badge_size, badge_size), (0,0,0,0))
            draw_b = ImageDraw.Draw(badge)
            draw_b.ellipse((0, 0, badge_size-1, badge_size-1), fill="white", outline="#e0e0e0", width=2)
            badge.paste(src, ((badge_size - src.width) // 2, (badge_size - src.height) // 2), src)
            canvas.paste(badge, (cx - (badge.width // 2), cy - (badge.height // 2)), badge)
        except: pass

def draw_ticker_line(canvas, text, x_cfg, y_cfg, font_path, color):
    """
    Draws Ticker/Label Text with VISIBILITY FIX.
    Added strict black outline stroke.
    """
    draw = ImageDraw.Draw(canvas)
    W, H = canvas.size
    is_newspaper_centered = x_cfg > 400
    start_font_size = 55 if is_newspaper_centered else 45
    t_font = core.load_font(font_path, start_font_size)
    max_w = 700 if is_newspaper_centered else 300
    while t_font.getlength(text) > max_w and start_font_size > 25:
        start_font_size -= 4; t_font = core.load_font(font_path, start_font_size)
        
    if is_newspaper_centered:
        center_x = W // 2
        draw.text((center_x, y_cfg), text, font=t_font, fill=color, anchor="mm", stroke_width=3, stroke_fill="black")
    elif x_cfg < 100:
        draw.text((x_cfg, y_cfg), text, font=t_font, fill=color, anchor="lm", stroke_width=3, stroke_fill="black")
    else:
        draw.text((x_cfg, y_cfg), text, font=t_font, fill=color, anchor="mm", stroke_width=3, stroke_fill="black")

def draw_social_icons(canvas, y_pos):
    W, H = canvas.size
    icons = ["like", "subscribe", "bell", "share"]
    icon_size = 100; spacing = 40
    total_w = (len(icons) * icon_size) + ((len(icons)-1) * spacing)
    start_x = (W - total_w) // 2
    draw = ImageDraw.Draw(canvas)
    for i, name in enumerate(icons):
        if name in ICONS:
            try:
                buf = io.BytesIO()
                cairosvg.svg2png(bytestring=ICONS[name], write_to=buf, output_height=icon_size)
                buf.seek(0)
                icon_img = Image.open(buf).convert("RGBA")
                cx = int(start_x + (i * (icon_size + spacing)) + (icon_size/2))
                cy = int(y_pos + (icon_size/2))
                draw.ellipse([cx-60, cy-60, cx+60, cy+60], fill=(255, 255, 255, 40), outline="white", width=3)
                data = np.array(icon_img); r, g, b, a = data.T
                white_areas = (a > 0); data[..., :-1][white_areas.T] = (255, 255, 255)
                icon_img = Image.fromarray(data)
                canvas.paste(icon_img, (int(cx-icon_size//2), int(cy-icon_size//2)), icon_img)
            except: pass

def render_hook_only_layer(hook_text):
    """
    Renders a transparent layer containing ONLY the Kinetic Hook text.
    Used for the first few seconds of the video.
    """
    W, H = 1080, 1920
    canvas = Image.new("RGBA", (W, H), (0,0,0,0))
    if not hook_text: return canvas
    draw = ImageDraw.Draw(canvas)
    
    font_path = os.path.join(ASSETS_DIR, "fonts", "Oswald-Bold.ttf")
    if not os.path.exists(font_path): font_path = os.path.join(ASSETS_DIR, "fonts", "Montserrat-Bold.ttf")

    target_size = 110; font = core.load_font(font_path, target_size)
    max_w = W * 0.90
    lines = core.wrap_text_pil(hook_text.upper(), font, max_w)
    
    while len(lines) > 4 and target_size > 60:
        target_size -= 10; font = core.load_font(font_path, target_size)
        lines = core.wrap_text_pil(hook_text.upper(), font, max_w)
        
    current_y = 300 
    for line in lines:
        for adj in [(-4,-4), (4,4), (-4,4), (4,-4), (0,4), (0,-4), (4,0), (-4,0)]:
            draw.text((W/2 + adj[0], current_y + adj[1]), line, font=font, fill="black", anchor="mm")
        draw.text((W/2, current_y), line, font=font, fill="#FFD700", anchor="mm")
        current_y += target_size * 1.1
    return canvas

def render_overlay_layer(data, theme_key):
    ticker = data.get('ticker', 'NEWS'); icon = data.get('icon', None)
    headline = data.get('headline', ''); summary = data.get('summary', '')
    is_outro = data.get('is_outro', False); cfg = THEMES[theme_key]
    effect = cfg.get('effect', 'none')
    base = Image.new("RGBA", (1080, 1920), (0,0,0,0))
    plate_path = os.path.join(ASSETS_DIR, "themes", cfg['overlay_asset'])
    if os.path.exists(plate_path):
        try: base.paste(Image.open(plate_path).convert("RGBA"), (0,0), Image.open(plate_path).convert("RGBA"))
        except: pass
    draw = ImageDraw.Draw(base)
    font_h_path = os.path.join(ASSETS_DIR, "fonts", cfg['fonts']['header'])
    font_b_path = os.path.join(ASSETS_DIR, "fonts", cfg['fonts']['body'])
    
    if 'layout' in cfg and 'logo' in cfg['layout']:
        logo_x, logo_y = cfg['layout']['logo']
        draw_hero_logo(base, icon, logo_y)
    
    if 'ticker' in cfg['layout']:
        tx, ty = cfg['layout']['ticker']
        t_col = cfg['colors'].get('ticker', 'white')
        draw_ticker_line(base, ticker, tx, ty, font_h_path, t_col)

    hx, hy, hw = cfg['layout']['header']
    target_h_size = 70; font_h = core.load_font(font_h_path, target_h_size)
    wrapped_h = core.wrap_text_pil(headline.upper(), font_h, hw)
    while (len(wrapped_h) > 2) and target_h_size > 35:
        target_h_size -= 5; font_h = core.load_font(font_h_path, target_h_size)
        wrapped_h = core.wrap_text_pil(headline.upper(), font_h, hw)
    curr_y = hy
    for line in wrapped_h:
        draw_text_with_effect(draw, (hx, curr_y), line, font_h, cfg['colors']['header'], effect)
        curr_y += font_h.size * 1.2

    bx, by, bw = cfg['layout']['body']
    curr_y = max(by, curr_y + 30); target_b_size = 50
    font_b = core.load_font(font_h_path, target_b_size)
    wrapped_b = core.wrap_text_pil(summary, font_b, bw)
    max_body_lines = 4
    while (len(wrapped_b) > max_body_lines) and target_b_size > 24:
        target_b_size -= 4; font_b = core.load_font(font_h_path, target_b_size)
        wrapped_b = core.wrap_text_pil(summary, font_b, bw)
    if len(wrapped_b) > max_body_lines: wrapped_b = wrapped_b[:max_body_lines]; wrapped_b[-1] += "..."
    for line in wrapped_b:
        draw.text((bx, curr_y), line, font=font_b, fill=cfg['colors']['body'])
        curr_y += font_b.size * 1.3
    
    if is_outro:
        # Move icons to Upper Half to clear bottom area
        draw_social_icons(base, 600)

    return base