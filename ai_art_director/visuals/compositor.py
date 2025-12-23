# ai_art_director/visuals/compositor.py
# v27.8.0 - Top Center Logo

import os
import io
import numpy as np
import cairosvg
from PIL import Image, ImageDraw
from ..config import ASSETS_DIR, ICONS
from .theme_config import THEMES
from . import core
from ..story_runners_refactored.background_manager import BackgroundManager

bg_manager = BackgroundManager()

# ... (get_smart_background_path & draw_text_with_effect remain unchanged) ...
def get_smart_background_path(ticker, headline, mode, specific_image=None):
    img_path = None
    
    # 1. User Specified Image
    if specific_image:
        # Define candidate paths
        candidates = [
            specific_image, # Absolute or CWD relative
            os.path.join(ASSETS_DIR, "bgImage", specific_image),
            os.path.join(ASSETS_DIR, "custom_news", specific_image),
            os.path.join(ASSETS_DIR, specific_image) # Root asset check
        ]
        
        for p in candidates:
            if os.path.exists(p):
                img_path = p
                print(f"      ✅ Found Local Image: {os.path.basename(p)}")
                break
        
        if not img_path:
            print(f"      ⚠️  Image '{specific_image}' not found in assets/bgImage or assets/custom_news")

    # 2. Ticker Match (Auto-Magic)
    if not img_path:
        clean = ticker.replace(".NS", "").replace(".BO", "").strip()
        # Look for {TICKER}.jpg in bgImage
        candidates = [
            os.path.join(ASSETS_DIR, "bgImage", f"{clean}.jpg"),
            os.path.join(ASSETS_DIR, "bgImage", f"{clean}.png"),
            os.path.join(ASSETS_DIR, "bgImage", f"{clean}.jpeg")
        ]
        for p in candidates:
            if os.path.exists(p):
                img_path = p
                print(f"      ✅ Found Ticker Image: {os.path.basename(p)}")
                break
    
    # 3. Pexels Fallback
    if not img_path:
        # print(f"      🔍 Searching Pexels for: {headline[:20]}...")
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

def draw_hero_logo(canvas, icon_name, y_limit_top):
    """Draws Logo at Top Center (Above content)"""
    if not icon_name: return
    
    W, H = canvas.size
    icon_size = 180  # Much bigger for Hero position
    cx = W // 2
    
    # Position: ~150px above the header start
    cy = max(150, y_limit_top - 150)
    
    icon_img = None
    
    # 1. Try Asset File
    logo_dir = os.path.join(ASSETS_DIR, "Logo")
    for fname in [icon_name, f"{icon_name}.png", f"{icon_name}.jpg"]:
        p = os.path.join(logo_dir, fname)
        if os.path.exists(p):
            try:
                logo_raw = Image.open(p).convert("RGBA")
                # Resize
                logo_raw.thumbnail((icon_size, icon_size), Image.Resampling.LANCZOS)
                
                # Create White Badge Background
                badge_size = icon_size + 20
                badge = Image.new("RGBA", (badge_size, badge_size), (0,0,0,0))
                draw_b = ImageDraw.Draw(badge)
                draw_b.ellipse((0, 0, badge_size, badge_size), fill="white", outline="#333", width=2)
                
                # Center logo in badge
                lx = (badge_size - logo_raw.width) // 2
                ly = (badge_size - logo_raw.height) // 2
                
                # Circular Mask for Logo itself
                mask = Image.new("L", logo_raw.size, 0)
                ImageDraw.Draw(mask).ellipse((0, 0, logo_raw.size[0], logo_raw.size[1]), fill=255)
                
                badge.paste(logo_raw, (lx, ly), mask)
                icon_img = badge
                break
            except: pass

    # 2. Try Built-in Icon (Fallback)
    if not icon_img and icon_name in ICONS:
        try:
            buf = io.BytesIO()
            cairosvg.svg2png(bytestring=ICONS[icon_name], write_to=buf, output_height=icon_size)
            buf.seek(0)
            icon_img = Image.open(buf).convert("RGBA")
        except: pass

    if icon_img:
        paste_x = cx - (icon_img.width // 2)
        paste_y = cy - (icon_img.height // 2)
        canvas.paste(icon_img, (paste_x, paste_y), icon_img)

def draw_ticker_line(canvas, text, x, y, font, color):
    """Draws JUST Ticker Text (No Icon)"""
    draw = ImageDraw.Draw(canvas)
    draw.text((x, y), text, font=font, fill=color)

def draw_social_icons(canvas, y_pos):
    W, H = canvas.size
    icons = ["like", "subscribe", "bell", "share"]
    icon_size = 100
    spacing = 40
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
                data = np.array(icon_img)
                r, g, b, a = data.T
                white_areas = (a > 0)
                data[..., :-1][white_areas.T] = (255, 255, 255)
                icon_img = Image.fromarray(data)
                canvas.paste(icon_img, (int(cx-icon_size//2), int(cy-icon_size//2)), icon_img)
            except: pass

def render_overlay_layer(data, theme_key):
    ticker = data.get('ticker', 'NEWS')
    icon = data.get('icon', None)
    headline = data.get('headline', '')
    summary = data.get('summary', '')
    is_outro = data.get('is_outro', False)
    cfg = THEMES[theme_key]
    effect = cfg.get('effect', 'none')

    base = Image.new("RGBA", (1080, 1920), (0,0,0,0))
    plate_path = os.path.join(ASSETS_DIR, "themes", cfg['overlay_asset'])
    if os.path.exists(plate_path):
        try:
            plate = Image.open(plate_path).convert("RGBA")
            base.paste(plate, (0,0), plate)
        except: pass

    draw = ImageDraw.Draw(base)
    font_h_path = os.path.join(ASSETS_DIR, "fonts", cfg['fonts']['header'])
    font_b_path = os.path.join(ASSETS_DIR, "fonts", cfg['fonts']['body'])

    # --- HERO LOGO (TOP CENTER) ---
    # We pass the header Y position so we know where to sit above
    header_y_start = cfg['layout']['header'][1]
    draw_hero_logo(base, icon, header_y_start)

    # --- TICKER ---
    if 'ticker' in cfg['layout']:
        tx, ty = cfg['layout']['ticker']
        t_font = core.load_font(font_h_path, 35)
        t_col = cfg['colors'].get('ticker', 'white')
        draw_ticker_line(base, ticker, tx, ty, t_font, t_col)

    # --- HEADER ---
    hx, hy, hw = cfg['layout']['header']
    target_h_size = 70
    font_h = core.load_font(font_h_path, target_h_size)
    wrapped_h = core.wrap_text_pil(headline.upper(), font_h, hw)
    
    while (len(wrapped_h) > 2) and target_h_size > 35:
        target_h_size -= 5
        font_h = core.load_font(font_h_path, target_h_size)
        wrapped_h = core.wrap_text_pil(headline.upper(), font_h, hw)

    curr_y = hy
    for line in wrapped_h:
        draw_text_with_effect(draw, (hx, curr_y), line, font_h, cfg['colors']['header'], effect)
        curr_y += font_h.size * 1.2

    # --- BODY ---
    bx, by, bw = cfg['layout']['body']
    curr_y = max(by, curr_y + 30)
    
    target_b_size = 50
    font_b = core.load_font(font_b_path, target_b_size)
    wrapped_b = core.wrap_text_pil(summary, font_b, bw)
    
    max_body_lines = 4
    while (len(wrapped_b) > max_body_lines) and target_b_size > 24:
        target_b_size -= 4
        font_b = core.load_font(font_b_path, target_b_size)
        wrapped_b = core.wrap_text_pil(summary, font_b, bw)
        
    if len(wrapped_b) > max_body_lines: 
        wrapped_b = wrapped_b[:max_body_lines]; wrapped_b[-1] += "..."

    for line in wrapped_b:
        draw_text_with_effect(draw, (bx, curr_y), line, font_b, cfg['colors']['body'], "none")
        curr_y += font_b.size * 1.3

    if is_outro: draw_social_icons(base, 1350)

    return base