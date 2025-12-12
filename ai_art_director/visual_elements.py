# ai_art_director/visual_elements.py
# v25.5.0 - Intro Headlines, Glass Header Shrink & Global Shifts

import os
import random
import numpy as np
import math
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import cairosvg
import io
from moviepy.editor import ImageClip, ColorClip

from . import config
from . import utils

# --- HELPER FUNCTIONS ---
def load_font(path, size):
    try: return ImageFont.truetype(path, size)
    except OSError:
        try: return ImageFont.truetype("Arial", size)
        except: return ImageFont.load_default()

def apply_random_animation(clip, start_time, slide_duration, size):
    return clip.set_start(start_time).set_duration(slide_duration).fadein(0.5)

def create_pan_zoom_clip(duration, bg_path, size):
    bg_color = tuple(int(config.BG_COLOR.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    if not bg_path or not os.path.exists(bg_path): return ColorClip(size=size, color=bg_color, duration=duration)
    try:
        img = Image.open(bg_path)
        img_w, img_h = img.size
        target_w, target_h = size
        scale = max(target_w/img_w, target_h/img_h) * 1.1
        new_w, new_h = int(img_w * scale), int(img_h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - target_w) // 2; top = (new_h - target_h) // 2
        img = img.crop((left, top, left + target_w, top + target_h))
        clip = ImageClip(np.array(img)).set_duration(duration)
        return clip.resize(lambda t: 1 + 0.05 * t/duration)
    except: return ColorClip(size=size, color=bg_color, duration=duration)

def create_blurred_image(image_path, output_path, blur_radius=15):
    try:
        with Image.open(image_path) as img:
            blurred = img.convert('RGB').filter(ImageFilter.GaussianBlur(blur_radius))
            blurred.save(output_path)
            return output_path
    except: return None

def _paste_safe_logo(canvas, logo, cx, cy, max_w, max_h):
    """Draws logo with white backing badge for visibility"""
    if not logo: return
    try:
        badge_size = min(int(max_w), int(max_h))
        if badge_size < 50: badge_size = 50
        badge = Image.new("RGBA", (badge_size, badge_size), (0,0,0,0))
        draw_badge = ImageDraw.Draw(badge)
        draw_badge.ellipse([2, 2, badge_size-2, badge_size-2], fill=(255, 255, 255, 240), outline="white", width=2)
        
        padding = int(badge_size * 0.15)
        target_icon_w = badge_size - (padding * 2)
        target_icon_h = badge_size - (padding * 2) # Explicitly set height target

        logo_ratio = logo.width / logo.height
        if logo_ratio > 1:
            new_w = target_icon_w
            new_h = int(target_icon_w / logo_ratio)
        else:
            new_h = target_icon_h
            new_w = int(target_icon_h * logo_ratio)
            
        resized_logo = logo.resize((new_w, new_h), Image.Resampling.LANCZOS)
        bx = int((badge_size - new_w) / 2)
        by = int((badge_size - new_h) / 2)
        badge.paste(resized_logo, (bx, by), resized_logo if resized_logo.mode == 'RGBA' else None)
        
        paste_x = int(cx - (badge_size / 2))
        paste_y = int(cy - (badge_size / 2))
        canvas.paste(badge, (paste_x, paste_y), badge)
    except Exception as e:
        print(f"      - ❌ Safe Logo Render Error: {e}")

# --- 2. CARD ENGINE ---

def draw_stock_card(draw, x, y, w, h, name, font_path, theme_accent, headline=None):
    """
    Draws the card background, name, AND optional headline.
    Returns the LOGO CENTER coordinates (adjusted to avoid overlapping text).
    """
    radius = 20
    bg_color = (20, 20, 25, 230)
    border_color = (200, 200, 200, 80)
    
    # Draw Box
    try: draw.rounded_rectangle([x, y, x+w, y+h], radius=radius, fill=bg_color, outline=border_color, width=2)
    except AttributeError: draw.rectangle([x, y, x+w, y+h], fill=bg_color, outline=border_color, width=2)

    # 1. Header (Company Name)
    header_h = max(50, h * 0.20)
    font_size = 40 if w > 300 else 30
    name_font = load_font(font_path, font_size)
    padding = 10
    
    # Shrink name to fit
    while name_font.getlength(name) > (w - padding*2) and font_size > 12:
        font_size -= 2
        name_font = load_font(font_path, font_size)
    
    draw.text((x + w/2, y + header_h/2), name, font=name_font, fill="white", anchor="mm")
    draw.line([(x + 20, y + header_h), (x + w - 20, y + header_h)], fill=theme_accent, width=3)
    
    logo_y_start = y + header_h + padding
    
    # 2. Headline (New Feature)
    if headline:
        # Define headline area (next 25% of height)
        hl_area_h = h * 0.25
        hl_font_size = 24 if w > 300 else 18
        hl_font = load_font(font_path, hl_font_size)
        
        # Shorten text if needed
        clean_hl = headline if len(headline) < 50 else headline[:47] + "..."
        lines = utils.wrap_text_pil(clean_hl, hl_font, w - padding*2)
        if len(lines) > 2: lines = lines[:2] # Max 2 lines
        
        # Draw lines
        text_y = logo_y_start
        for line in lines:
            draw.text((x + w/2, text_y), line, font=hl_font, fill="#DDDDDD", anchor="mt")
            text_y += hl_font_size * 1.2
            
        # Push logo down
        logo_y_start += hl_area_h

    # 3. Logo Area Calculation
    logo_h_avail = (y + h) - logo_y_start - padding
    if logo_h_avail < 0: logo_h_avail = 0
    logo_w_avail = w - (padding * 2)
    
    cx = x + w/2
    cy = logo_y_start + logo_h_avail/2
    
    # Return CENTER coordinates for safe pasting
    return cx, cy, logo_w_avail, logo_h_avail

# --- 3. SLIDE RENDERERS ---

TITLE_TRANSLATIONS = {
    'en': {'news': "Breaking News", 'deepdive': "Deep Dive Analysis", 'comparison': "Head-to-Head", 'spotlight': "Spotlight Analysis", 'custom_news': "Special Update", 'news_roundup': "Market Roundup"},
    'hi': {'news': "ताज़ा ख़बर", 'deepdive': "गहन विश्लेषण", 'comparison': "तुलनात्मक विश्लेषण", 'spotlight': "स्पॉटलाइट एनालिसिस"}
}

def render_intro_slide(slide_info, story_type, assets, theme, duration, size):
    VIDEO_W, VIDEO_H = size
    font_path = theme['font']
    lang = theme.get('lang', 'en') 

    canvas = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(canvas)
    
    titles = TITLE_TRANSLATIONS.get(lang, TITLE_TRANSLATIONS['en'])
    title_text = titles.get(story_type, TITLE_TRANSLATIONS['en'].get(story_type, "Analysis"))
    
    title_font = load_font(font_path, 60)
    # Shifted Title Up (0.10)
    draw.text((VIDEO_W/2+2, VIDEO_H * 0.10+2), title_text, font=title_font, fill="black", anchor="mm")
    draw.text((VIDEO_W/2, VIDEO_H * 0.10), title_text, font=title_font, fill="white", anchor="mm")

    # --- MULTI-STOCK GRID LOGIC ---
    if story_type in ['comparison', 'news_roundup']:
        names = slide_info.get('names', [])
        logos = slide_info.get('logos', [])
        headlines = slide_info.get('headlines', []) # New: List of headlines
        
        count = len(names)
        start_y, end_y = VIDEO_H * 0.15, VIDEO_H * 0.85
        avail_h, avail_w = end_y - start_y, VIDEO_W * 0.92
        margin_x = (VIDEO_W - avail_w) / 2
        card_coords = [] 
        
        if count == 2:
            if VIDEO_W < VIDEO_H: # Portrait
                h_each = avail_h / 2.1
                card_coords = [(margin_x, start_y, avail_w, h_each), (margin_x, end_y - h_each, avail_w, h_each)]
                draw.ellipse([VIDEO_W/2 - 35, (start_y + avail_h/2) - 35, VIDEO_W/2 + 35, (start_y + avail_h/2) + 35], fill=theme['accent'], outline="white", width=3)
                draw.text((VIDEO_W/2, start_y + avail_h/2), "VS" if story_type == 'comparison' else "&", font=load_font(font_path, 35), fill="white", anchor="mm")
            else: # Landscape
                w_each = avail_w / 2.1
                card_coords = [(margin_x, start_y + 40, w_each, avail_h - 80), (VIDEO_W - margin_x - w_each, start_y + 40, w_each, avail_h - 80)]
        elif count == 3:
            h_each = avail_h / 2.2; w_bottom = (avail_w / 2) - 10
            card_coords = [
                (margin_x + avail_w/4, start_y, avail_w/2, h_each), 
                (margin_x, end_y - h_each, w_bottom, h_each), 
                (VIDEO_W - margin_x - w_bottom, end_y - h_each, w_bottom, h_each)
            ]
        elif count >= 4:
            h_each = avail_h / 2.1; w_each = (avail_w / 2) - 10
            card_coords = [
                (margin_x, start_y, w_each, h_each), 
                (VIDEO_W - margin_x - w_each, start_y, w_each, h_each), 
                (margin_x, end_y - h_each, w_each, h_each), 
                (VIDEO_W - margin_x - w_each, end_y - h_each, w_each, h_each)
            ]

        # Draw Cards & Safe Logos
        for i, (cx, cy, cw, ch) in enumerate(card_coords):
            if i < len(names):
                # Get headline if available (and relevant)
                hl = headlines[i] if i < len(headlines) and headlines else None
                
                # Draw Card (Name + Headline) - Returns new center for Logo
                lcx, lcy, lw, lh = draw_stock_card(draw, cx, cy, cw, ch, names[i], font_path, theme['accent'], headline=hl)
                
                # Draw Safe Logo at calculated position
                if i < len(logos) and logos[i]:
                    _paste_safe_logo(canvas, logos[i], lcx, lcy, lw, lh)

    else:
        # --- SINGLE STOCK LOGIC ---
        logo = assets.get('logo')
        if logo:
            hero_w = int(VIDEO_W * 0.35)
            hero_h = int(VIDEO_W * 0.35)
            cx = VIDEO_W / 2
            cy = VIDEO_H * 0.30
            _paste_safe_logo(canvas, logo, cx, cy, hero_w, hero_h)

        comp_name = slide_info.get('text', '')
        name_size = 80
        comp_font = load_font(font_path, name_size)
        max_width = VIDEO_W * 0.95
        while name_size > 30:
            try: w = comp_font.getlength(comp_name)
            except: w = 100
            if w < max_width: break
            name_size -= 5
            comp_font = load_font(font_path, name_size)
            
        text_y = VIDEO_H * 0.60
        draw.text((VIDEO_W/2+3, text_y+3), comp_name, font=comp_font, fill="black", anchor="mm")
        draw.text((VIDEO_W/2, text_y), comp_name, font=comp_font, fill=theme['accent'], stroke_width=2, stroke_fill="black", anchor="mm")

    return ImageClip(np.array(canvas)).set_duration(duration)


def render_glass_news_slide(slide_info, theme, duration, size):
    VIDEO_W, VIDEO_H = size
    font_path = theme['font']
    canvas = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(canvas)
    
    # 1. Glass Card Background (Bottom 70%)
    card_h = VIDEO_H * 0.70
    card_y = VIDEO_H - card_h - (VIDEO_H * 0.15) 
    margin = 40
    
    draw.rounded_rectangle(
        [margin, card_y, VIDEO_W - margin, card_y + card_h],
        radius=30,
        fill=(10, 10, 15, 210), 
        outline=(255, 255, 255, 50),
        width=2
    )
    
    # 2. Header
    header_h = 120
    header_y = card_y + 20
    
    # Logo
    logo = slide_info.get('logo')
    if logo:
        _paste_safe_logo(canvas, logo, margin + 80, header_y + 60, 100, 100)
    
    # Company Name
    company_name = slide_info.get('company', '')
    name_x = margin + 160
    max_name_w = (VIDEO_W - margin - 20) - name_x
    name_size = 50
    name_font = load_font(font_path, name_size)
    
    while name_font.getlength(company_name) > max_name_w and name_size > 20:
        name_size -= 4
        name_font = load_font(font_path, name_size)
        
    draw.text((name_x, header_y + 60), company_name, font=name_font, fill="white", anchor="lm")
    draw.line([(margin + 20, header_y + 120), (VIDEO_W - margin - 20, header_y + 120)], fill=theme['accent'], width=2)
    
    # 3. Headline
    headline = slide_info.get('text', '')
    content_y_center = header_y + 120 + (card_h - 120) / 2
    
    hl_font_size = 60
    hl_font = load_font(font_path, hl_font_size)
    lines = utils.wrap_text_pil(headline, hl_font, (VIDEO_W - margin*2) * 0.9)
    while len(lines) > 5 and hl_font_size > 30:
        hl_font_size -= 5
        hl_font = load_font(font_path, hl_font_size)
        lines = utils.wrap_text_pil(headline, hl_font, (VIDEO_W - margin*2) * 0.9)
        
    text_h = len(lines) * (hl_font_size * 1.3)
    start_text_y = content_y_center - (text_h / 2)
    
    last_text_y = 0
    for i, line in enumerate(lines):
        line_y = start_text_y + (i * hl_font_size * 1.3)
        draw.text((VIDEO_W/2, line_y), line, font=hl_font, fill="white", anchor="mm")
        last_text_y = line_y

    # --- SOURCE ATTRIBUTION (FIXED STYLE) ---
    source = slide_info.get('source', '')
    if source:
        # Place below text with padding
        source_y = last_text_y + hl_font_size + 20
        
        # Safety clamp
        if source_y > (card_y + card_h - 30):
            source_y = card_y + card_h - 30
            
        source_font = load_font(font_path, 20) # Small 20px
        source_text = f"- Source: {source}"
        draw.text((VIDEO_W/2, source_y), source_text, font=source_font, fill="#AAAAAA", anchor="mm")
    # ----------------------------------------
        
    return ImageClip(np.array(canvas)).set_duration(duration)


def render_sector_slide(slide_info, theme, duration, size):
    VIDEO_W, VIDEO_H = size
    font_path = theme['font']
    canvas = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(canvas)
    parts = slide_info['text'].split('\n'); parts = [p for p in parts if p.strip()]
    mcap = parts[1] if len(parts) > 1 else "N/A"
    sector = parts[3] if len(parts) > 3 else (parts[2] if len(parts) > 2 else "N/A")
    
    # Box adjusted slightly higher
    box_w = VIDEO_W * 0.9; box_h = VIDEO_H * 0.6
    bx = (VIDEO_W - box_w) / 2
    by = (VIDEO_H - box_h) / 2 - 50
    
    draw.rectangle([bx, by, bx + box_w, by + box_h], fill=(0, 0, 0, 180), outline="white", width=2)
    center_x = VIDEO_W / 2; lbl_font = load_font(font_path, 45)
    max_text_width = box_w * 0.9; mcap_size = 90; val_font = load_font(font_path, mcap_size)
    while mcap_size > 40:
        w = val_font.getlength(mcap) if hasattr(val_font, 'getlength') else val_font.getmask(mcap).getbbox()[2]
        if w < max_text_width: break
        mcap_size -= 5; val_font = load_font(font_path, mcap_size)
    y_cursor = by + (box_h * 0.25)
    draw.text((center_x, y_cursor - 50), "MARKET CAP", font=lbl_font, fill="#AAAAAA", anchor="mm")
    draw.text((center_x+3, y_cursor+3), mcap, font=val_font, fill="black", anchor="mm")
    draw.text((center_x, y_cursor), mcap, font=val_font, fill=theme['accent'], anchor="mm")
    line_y = by + (box_h * 0.5); draw.line([(bx + 40, line_y), (bx + box_w - 40, line_y)], fill="white", width=2)
    sector_size = 60; sec_font = load_font(font_path, sector_size)
    while sector_size > 30:
        w = sec_font.getlength(sector) if hasattr(sec_font, 'getlength') else sec_font.getmask(sector).getbbox()[2]
        if w < max_text_width: break
        sector_size -= 4; sec_font = load_font(font_path, sector_size)
    y_cursor = by + (box_h * 0.75)
    draw.text((center_x, y_cursor - 40), "SECTOR", font=lbl_font, fill="#AAAAAA", anchor="mm")
    draw.text((center_x+2, y_cursor+2), sector, font=sec_font, fill="black", anchor="mm")
    draw.text((center_x, y_cursor + 10), sector, font=sec_font, fill="white", anchor="mm")
    return ImageClip(np.array(canvas)).set_duration(duration)

def render_management_slide(slide_info, theme, duration, size):
    VIDEO_W, VIDEO_H = size; font_path = theme['font']
    canvas = Image.new("RGBA", size, (0,0,0,0)); draw = ImageDraw.Draw(canvas)
    
    # Box shifted up
    box_w, box_h = VIDEO_W * 0.85, VIDEO_H * 0.5
    bx = (VIDEO_W - box_w)/2
    by = (VIDEO_H - box_h)/2 - 50
    
    draw.rectangle([bx, by, bx+box_w, by+box_h], fill=(0,0,0,160), outline=theme['accent'], width=3)
    parts = [p.strip() for p in slide_info['text'].split('\n') if p.strip()]
    name = parts[1] if len(parts) > 1 else "N/A"
    lbl_font = load_font(font_path, 45)
    draw.rectangle([bx, by, bx+box_w, by+80], fill=theme['accent'])
    draw.text((VIDEO_W/2, by+40), "LEADERSHIP", font=lbl_font, fill="white", anchor="mm")
    cx, cy = VIDEO_W/2, by + 180; r = 50
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline="white", width=3)
    draw.ellipse([cx-20, cy-25, cx+20, cy+15], fill="white")
    draw.pieslice([cx-35, cy+10, cx+35, cy+80], 180, 360, fill="white")
    nm_font = load_font(font_path, 65); name_lines = utils.wrap_text_pil(name, nm_font, box_w * 0.9)
    text_y = cy + 100
    for line in name_lines:
        draw.text((VIDEO_W/2, text_y), line, font=nm_font, fill="white", anchor="mm"); text_y += 70
    draw.text((VIDEO_W/2, text_y + 20), "Chief Executive Officer", font=lbl_font, fill="#aaaaaa", anchor="mm")
    return ImageClip(np.array(canvas)).set_duration(duration)


def render_news_slide(slide_info, icon_svg, theme, duration, size):
    VIDEO_W, VIDEO_H = size
    canvas = Image.new("RGBA", size, (0,0,0,0)); draw = ImageDraw.Draw(canvas)
    font = load_font(theme['font'], 70)
    lines = utils.wrap_text_pil(slide_info['text'], font, VIDEO_W * 0.8)
    
    y = VIDEO_H * 0.35
    for line in lines:
        draw.text((VIDEO_W/2+3, y+3), line, font=font, fill="black", anchor="mm")
        draw.text((VIDEO_W/2, y), line, font=font, fill="white", anchor="mm")
        y += 80
        
    # --- SOURCE ATTRIBUTION (FIXED STYLE) ---
    source = slide_info.get('source', '')
    if source:
        source_y = VIDEO_H * 0.80 
        source_font = load_font(theme['font'], 20) # Small 20px
        source_text = f"- Source: {source}"
        draw.text((VIDEO_W/2, source_y), source_text, font=source_font, fill="#CCCCCC", anchor="mm")
    # ----------------------------------------

    return [ImageClip(np.array(canvas)).set_duration(duration)]

def render_summary_slide(slide_info, theme, duration, size):
    VIDEO_W, VIDEO_H = size
    canvas = Image.new("RGBA", size, (0,0,0,0)); draw = ImageDraw.Draw(canvas)
    font = load_font(theme['font'], 60)
    lines = utils.wrap_text_pil(slide_info['text'], font, VIDEO_W * 0.8)
    
    y = VIDEO_H * 0.35
    for line in lines:
        draw.text((VIDEO_W/2+3, y+3), line, font=font, fill="black", anchor="mm")
        draw.text((VIDEO_W/2, y), line, font=font, fill="white", anchor="mm")
        y += 70
    return [ImageClip(np.array(canvas)).set_duration(duration)]

def render_chart_slide(slide_info, size, duration):
    path = slide_info.get('path')
    if path and os.path.exists(path):
        img = Image.open(path).convert("RGBA")
        img.thumbnail((int(size[0]*0.95), int(size[1]*0.95)), Image.Resampling.LANCZOS)
        bg = Image.new("RGBA", size, (0,0,0,0))
        bg.paste(img, (int((size[0]-img.width)/2), int((size[1]-img.height)/2) - 50), img) 
        return [ImageClip(np.array(bg)).set_duration(duration)]
    return []

# CTA & Common
def _render_cta_common(slide_info, story_type, icon_svg, theme, duration, size, layout_type):
    VIDEO_W, VIDEO_H = size
    font_path = theme['font']
    story_theme = config.STORY_THEMES.get(story_type, config.STORY_THEMES['news'])
    canvas = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(canvas)
    
    icons = story_theme['cta_icons'][:]
    if story_type == 'comparison':
        if 'share' not in icons: icons.insert(0, 'share')
        if 'poll' in icons: icons.remove('poll')
        if icons[0] != 'share': icons.remove('share'); icons.insert(0, 'share')
    icons = icons[:4]
    
    positions = []
    if layout_type == "diamond" and len(icons) >= 4:
        cx, cy = VIDEO_W/2, VIDEO_H * 0.35; dist = VIDEO_W * 0.3 
        positions = [(cx, cy - dist), (cx - dist, cy), (cx + dist, cy), (cx, cy + dist)]
    elif layout_type == "grid":
        grid_w, grid_h = VIDEO_W * 0.7, VIDEO_H * 0.4; sx, sy = (VIDEO_W - grid_w)/2, VIDEO_H * 0.15; cw, ch = grid_w/2, grid_h/2 
        for i in range(4): r, c = divmod(i, 2); positions.append((sx + c*cw + cw/2, sy + r*ch + ch/2))
    elif layout_type == "circular":
        cx, cy = VIDEO_W/2, VIDEO_H * 0.35; rad = VIDEO_W * 0.25; step = 360 / len(icons) 
        for i in range(len(icons)): ang = math.radians(i*step - 90); positions.append((cx + rad*math.cos(ang), cy + rad*math.sin(ang)))
    else:
        sp = VIDEO_W / (len(icons) + 1); y = VIDEO_H * 0.35 
        for i in range(len(icons)): positions.append((sp*(i+1), y))

    icon_sz = 100
    lbl_font = load_font(font_path, 28)
    for i, name in enumerate(icons):
        if i >= len(positions): break
        px, py = positions[i]; bg_r = icon_sz / 2 + 15
        draw.ellipse([px - bg_r, py - bg_r, px + bg_r, py + bg_r], fill=(0,0,0,160))
        if name in icon_svg:
            try:
                buf = io.BytesIO(); cairosvg.svg2png(bytestring=icon_svg[name], write_to=buf, output_height=icon_sz)
                buf.seek(0); img = Image.open(buf).convert("RGBA")
                data = np.array(img); data[..., :-1][data[..., 3] > 0] = (255, 255, 255); img = Image.fromarray(data)
                canvas.paste(img, (int(px-icon_sz/2), int(py-icon_sz/2)), img)
            except: pass
        draw.text((px, py + bg_r + 20), name.capitalize(), font=lbl_font, fill="white", stroke_width=2, stroke_fill="black", anchor="mm")

    txt_h = VIDEO_H * 0.25
    draw.rectangle([0, VIDEO_H - txt_h - 20, VIDEO_W, VIDEO_H-20], fill=(0,0,0,200))
    txt = story_theme['cta_text']
    target_font_size = 50; t_font = load_font(font_path, target_font_size)
    lines = utils.wrap_text_pil(txt, t_font, VIDEO_W * 0.9)
    cy = VIDEO_H - txt_h + 10
    for line in lines:
        draw.text((VIDEO_W/2, cy), line, font=t_font, fill="white", anchor="mm"); cy += target_font_size * 1.3
    return ImageClip(np.array(canvas)).set_duration(duration)

def render_cta_slide_grid(s,st,v,t,d,z): return _render_cta_common(s,st,v,t,d,z,'grid')
def render_cta_slide_linear(s,st,v,t,d,z): return _render_cta_common(s,st,v,t,d,z,'linear')
def render_cta_slide_circular(s,st,v,t,d,z): return _render_cta_common(s,st,v,t,d,z,'circular')
def render_cta_slide_diamond(s,st,v,t,d,z): return _render_cta_common(s,st,v,t,d,z,'diamond')