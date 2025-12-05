# visual_elements.py
# v24.3.2 - Fixed Crash & Text Overflow

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

# --- 1. HELPER FUNCTIONS ---

def load_font(path, size):
    """Local helper to load fonts safely"""
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        try:
            return ImageFont.truetype("Arial", size)
        except OSError:
            return ImageFont.load_default()

def apply_random_animation(clip, start_time, slide_duration, size):
    # Simple fade in is safest
    return clip.set_start(start_time).set_duration(slide_duration).fadein(0.5)

def create_pan_zoom_clip(duration, bg_path, size):
    bg_color = tuple(int(config.BG_COLOR.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    
    if not bg_path or not os.path.exists(bg_path):
        return ColorClip(size=size, color=bg_color, duration=duration)
    
    try:
        img = Image.open(bg_path)
        img_w, img_h = img.size
        target_w, target_h = size
        
        # Resize to cover
        scale = max(target_w/img_w, target_h/img_h) * 1.1
        new_w, new_h = int(img_w * scale), int(img_h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Center crop
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        img = img.crop((left, top, left + target_w, top + target_h))
        
        clip = ImageClip(np.array(img)).set_duration(duration)
        return clip.resize(lambda t: 1 + 0.05 * t/duration) # Slow zoom
        
    except Exception:
        return ColorClip(size=size, color=bg_color, duration=duration)

def create_blurred_image(image_path, output_path, blur_radius=15):
    try:
        with Image.open(image_path) as img:
            blurred = img.convert('RGB').filter(ImageFilter.GaussianBlur(blur_radius))
            blurred.save(output_path)
            return output_path
    except: return None

# --- HELPER: Draw a Stock Card ---
def draw_stock_card(draw, x, y, w, h, logo, name, font_path, theme_accent):
    """Draws a modern, rounded card with a header for the stock name."""
    
    # 1. Style Constants
    radius = 20
    bg_color = (20, 20, 25, 230) # Dark, high opacity for readability
    border_color = (200, 200, 200, 80) # Subtle white border
    
    # 2. Draw Rounded Background
    # Note: standard PIL draw.rectangle doesn't support radius in older versions, 
    # but recent versions do. If this fails, it falls back to rectangle.
    try:
        draw.rounded_rectangle([x, y, x+w, y+h], radius=radius, fill=bg_color, outline=border_color, width=2)
    except AttributeError:
        draw.rectangle([x, y, x+w, y+h], fill=bg_color, outline=border_color, width=2)

    # 3. Header Calculation (Name Area)
    # Give the name the top 25% of the card, or minimum 60px
    header_h = max(60, h * 0.22)
    
    # 4. Draw Name (Shrink-to-Fit)
    font_size = 45
    if w < 300: font_size = 35 # Smaller starting font for small cards
    
    name_font = load_font(font_path, font_size)
    padding = 15
    
    # Shrink loop
    while name_font.getlength(name) > (w - padding*2) and font_size > 15:
        font_size -= 2
        name_font = load_font(font_path, font_size)
    
    text_x = x + w/2
    text_y = y + header_h/2
    
    draw.text((text_x, text_y), name, font=name_font, fill="white", anchor="mm")
    
    # 5. Draw Accent Separator Line
    line_y = y + header_h
    draw.line([(x + 20, line_y), (x + w - 20, line_y)], fill=theme_accent, width=3)
    
    # 6. Calculate Logo Area (Remaining space)
    logo_x = x + padding
    logo_y = line_y + padding
    logo_w = w - (padding * 2)
    logo_h = (y + h) - logo_y - padding
    
    # Safety check if card is too short
    if logo_h < 10: logo_h = 0
    
    # Return tuple for parent to paste the logo image
    return (int(logo_x), int(logo_y), int(logo_w), int(logo_h))

# --- 2. SLIDE RENDERERS ---

def render_intro_slide(slide_info, story_type, assets, theme, duration, size):
    VIDEO_W, VIDEO_H = size
    font_path = theme['font']
    
    canvas = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(canvas)
    
    # Main Title (Top 15%)
    title_text = "Deep Dive Analysis"
    if story_type == 'news': title_text = "Breaking News"
    elif story_type == 'comparison': title_text = "Head-to-Head"
    elif story_type == 'spotlight': title_text = "Spotlight Analysis"
    
    title_font = load_font(font_path, 60)
    draw.text((VIDEO_W/2+2, VIDEO_H * 0.12+2), title_text, font=title_font, fill="black", anchor="mm")
    draw.text((VIDEO_W/2, VIDEO_H * 0.12), title_text, font=title_font, fill="white", anchor="mm")

    # --- COMPARISON CARDS LOGIC ---
    if story_type == 'comparison':
        names = slide_info.get('names', [])
        logos = slide_info.get('logos', [])
        count = len(names)
        
        # Grid Area
        start_y = VIDEO_H * 0.20
        end_y = VIDEO_H * 0.90
        avail_h = end_y - start_y
        avail_w = VIDEO_W * 0.92
        margin_x = (VIDEO_W - avail_w) / 2
        
        card_coords = [] 
        
        # Layout Logic
        if count == 2:
            if VIDEO_W < VIDEO_H: # Portrait (Top/Bottom)
                h_each = avail_h / 2.1
                card_coords = [
                    (margin_x, start_y, avail_w, h_each),
                    (margin_x, end_y - h_each, avail_w, h_each)
                ]
                # VS Badge
                draw.ellipse([VIDEO_W/2 - 35, (start_y + avail_h/2) - 35, VIDEO_W/2 + 35, (start_y + avail_h/2) + 35], fill=theme['accent'], outline="white", width=3)
                draw.text((VIDEO_W/2, start_y + avail_h/2), "VS", font=load_font(font_path, 35), fill="white", anchor="mm")
            else: # Landscape (Left/Right)
                w_each = avail_w / 2.1
                card_coords = [
                    (margin_x, start_y + 40, w_each, avail_h - 80),
                    (VIDEO_W - margin_x - w_each, start_y + 40, w_each, avail_h - 80)
                ]
        elif count == 3:
            h_each = avail_h / 2.2
            w_bottom = (avail_w / 2) - 10
            card_coords = [
                (margin_x + avail_w/4, start_y, avail_w/2, h_each), 
                (margin_x, end_y - h_each, w_bottom, h_each), 
                (VIDEO_W - margin_x - w_bottom, end_y - h_each, w_bottom, h_each) 
            ]
        elif count >= 4:
            h_each = avail_h / 2.1
            w_each = (avail_w / 2) - 10
            card_coords = [
                (margin_x, start_y, w_each, h_each), 
                (VIDEO_W - margin_x - w_each, start_y, w_each, h_each), 
                (margin_x, end_y - h_each, w_each, h_each), 
                (VIDEO_W - margin_x - w_each, end_y - h_each, w_each, h_each) 
            ]

        # Draw Cards using Helper
        for i, (cx, cy, cw, ch) in enumerate(card_coords):
            if i < len(names):
                logo_img = logos[i] if i < len(logos) else None
                
                # Draw Card & Get Logo Area
                logo_dest = draw_stock_card(draw, cx, cy, cw, ch, logo_img, names[i], font_path, theme['accent'])
                
                # Paste Logo Center-Fit
                if logo_dest and logo_img:
                    try:
                        dest_x, dest_y, dest_w, dest_h = logo_dest
                        if dest_h > 10 and dest_w > 10:
                            l_copy = logo_img.copy()
                            
                            # Maintain Aspect Ratio
                            aspect = l_copy.width / l_copy.height
                            fit_w = min(dest_w, dest_h * aspect)
                            fit_h = fit_w / aspect
                            
                            # If still too tall
                            if fit_h > dest_h:
                                fit_h = dest_h
                                fit_w = fit_h * aspect
                                
                            # Scale down a bit (90%) for breathing room
                            fit_w *= 0.85
                            fit_h *= 0.85
                            
                            l_copy.thumbnail((int(fit_w), int(fit_h)), Image.Resampling.LANCZOS)
                            
                            paste_x = int(dest_x + (dest_w - l_copy.width)/2)
                            paste_y = int(dest_y + (dest_h - l_copy.height)/2)
                            
                            canvas.paste(l_copy, (paste_x, paste_y), l_copy if l_copy.mode == 'RGBA' else None)
                    except: pass

    else:
        # --- STANDARD SINGLE STOCK LOGIC ---
        if assets.get('logo'):
            try:
                logo = assets['logo'].copy()
                max_w, max_h = VIDEO_W * 0.6, VIDEO_H * 0.3
                logo.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
                lx = int((VIDEO_W - logo.width) / 2)
                ly = int((VIDEO_H - logo.height) / 2)
                canvas.paste(logo, (lx, ly), logo if logo.mode == 'RGBA' else None)
            except Exception: pass

        comp_name = slide_info.get('text', '')
        name_size = 80
        comp_font = load_font(font_path, name_size)
        max_width = VIDEO_W * 0.95
        while name_size > 30:
            w = comp_font.getlength(comp_name) if hasattr(comp_font, 'getlength') else comp_font.getmask(comp_name).getbbox()[2]
            if w < max_width: break
            name_size -= 5
            comp_font = load_font(font_path, name_size)
        
        draw.text((VIDEO_W/2 + 3, VIDEO_H * 0.75 + 3), comp_name, font=comp_font, fill="black", anchor="mm")
        draw.text((VIDEO_W/2, VIDEO_H * 0.75), comp_name, font=comp_font, fill=theme['accent'], anchor="mm")

    return ImageClip(np.array(canvas)).set_duration(duration)

def render_sector_slide(slide_info, theme, duration, size):
    """Renders Market Cap & Sector Info with Shrink-to-Fit text."""
    VIDEO_W, VIDEO_H = size
    font_path = theme['font']
    canvas = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(canvas)
    
    # Parse Data
    parts = slide_info['text'].split('\n')
    parts = [p for p in parts if p.strip()]
    mcap = parts[1] if len(parts) > 1 else "N/A"
    sector = parts[3] if len(parts) > 3 else (parts[2] if len(parts) > 2 else "N/A")
    
    # Determine Box Height
    box_w = VIDEO_W * 0.9
    box_h = VIDEO_H * 0.6
    bx = (VIDEO_W - box_w) / 2
    by = (VIDEO_H - box_h) / 2
    
    # Draw Semi-Transparent Dark Box
    draw.rectangle([bx, by, bx + box_w, by + box_h], fill=(0, 0, 0, 180), outline="white", width=2)
    center_x = VIDEO_W / 2
    
    # Fonts
    lbl_font = load_font(font_path, 45)
    
    # --- Dynamic Scaling for Market Cap ---
    max_text_width = box_w * 0.9 # Padding inside box
    mcap_size = 90
    val_font = load_font(font_path, mcap_size)
    
    # Shrink loop
    while mcap_size > 40:
        w = val_font.getlength(mcap) if hasattr(val_font, 'getlength') else val_font.getmask(mcap).getbbox()[2]
        if w < max_text_width:
            break
        mcap_size -= 5
        val_font = load_font(font_path, mcap_size)
    
    # Market Cap (Top Half)
    y_cursor = by + (box_h * 0.25)
    draw.text((center_x, y_cursor - 50), "MARKET CAP", font=lbl_font, fill="#AAAAAA", anchor="mm")
    
    # Draw Value with Shadow
    draw.text((center_x+3, y_cursor+3), mcap, font=val_font, fill="black", anchor="mm")
    draw.text((center_x, y_cursor), mcap, font=val_font, fill=theme['accent'], anchor="mm")
    
    # Divider Line
    line_y = by + (box_h * 0.5)
    draw.line([(bx + 40, line_y), (bx + box_w - 40, line_y)], fill="white", width=2)
    
    # Sector (Bottom Half) - Apply similar shrink logic if sector name is huge
    sector_size = 60
    sec_font = load_font(font_path, sector_size)
    while sector_size > 30:
        w = sec_font.getlength(sector) if hasattr(sec_font, 'getlength') else sec_font.getmask(sector).getbbox()[2]
        if w < max_text_width:
            break
        sector_size -= 4
        sec_font = load_font(font_path, sector_size)

    y_cursor = by + (box_h * 0.75)
    draw.text((center_x, y_cursor - 40), "SECTOR", font=lbl_font, fill="#AAAAAA", anchor="mm")
    
    draw.text((center_x+2, y_cursor+2), sector, font=sec_font, fill="black", anchor="mm")
    draw.text((center_x, y_cursor + 10), sector, font=sec_font, fill="white", anchor="mm")
    
    return ImageClip(np.array(canvas)).set_duration(duration)

def render_management_slide(slide_info, theme, duration, size):
    VIDEO_W, VIDEO_H = size
    font_path = theme['font']
    canvas = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(canvas)
    
    # Glass box
    box_w, box_h = VIDEO_W * 0.85, VIDEO_H * 0.5
    bx, by = (VIDEO_W - box_w)/2, (VIDEO_H - box_h)/2
    draw.rectangle([bx, by, bx+box_w, by+box_h], fill=(0,0,0,160), outline=theme['accent'], width=3)
    
    parts = [p.strip() for p in slide_info['text'].split('\n') if p.strip()]
    name = parts[1] if len(parts) > 1 else "N/A"
    
    lbl_font = load_font(font_path, 45)
    draw.rectangle([bx, by, bx+box_w, by+80], fill=theme['accent'])
    draw.text((VIDEO_W/2, by+40), "LEADERSHIP", font=lbl_font, fill="white", anchor="mm")
    
    cx, cy = VIDEO_W/2, by + 180
    r = 50
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline="white", width=3)
    draw.ellipse([cx-20, cy-25, cx+20, cy+15], fill="white")
    draw.pieslice([cx-35, cy+10, cx+35, cy+80], 180, 360, fill="white")
    
    nm_font = load_font(font_path, 65)
    name_lines = utils.wrap_text_pil(name, nm_font, box_w * 0.9)
    
    text_y = cy + 100
    for line in name_lines:
        draw.text((VIDEO_W/2, text_y), line, font=nm_font, fill="white", anchor="mm")
        text_y += 70
        
    draw.text((VIDEO_W/2, text_y + 20), "Chief Executive Officer", font=lbl_font, fill="#aaaaaa", anchor="mm")

    return ImageClip(np.array(canvas)).set_duration(duration)

# --- 3. CTA RENDERERS (Fixed Layouts & Visibility) ---

def _render_cta_common(slide_info, story_type, icon_svg, theme, duration, size, layout_type):
    VIDEO_W, VIDEO_H = size
    font_path = theme['font']
    story_theme = config.STORY_THEMES.get(story_type, config.STORY_THEMES['news'])
    
    canvas = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(canvas)
    
    # --- FIX: Explicitly prioritize Share for Comparison ---
    # Original was: ["poll", "like", "comment", "subscribe"]
    # New Order: ["share", "like", "comment", "subscribe"] (Replaced Poll with Share)
    
    icons = story_theme['cta_icons'][:] # Copy list
    
    if story_type == 'comparison':
        # Force 'share' to be first, remove 'poll' if desired
        if 'share' not in icons: icons.insert(0, 'share')
        if 'poll' in icons: icons.remove('poll')
        # Ensure 'share' is at index 0
        if icons[0] != 'share':
            icons.remove('share')
            icons.insert(0, 'share')
            
    icons = icons[:4] # Take top 4
    
    # --- LAYOUT LOGIC (Remains same) ---
    positions = []
    
    if layout_type == "diamond" and len(icons) >= 4:
        cx, cy = VIDEO_W/2, VIDEO_H * 0.4
        dist = VIDEO_W * 0.3
        positions = [
            (cx, cy - dist),      # Top
            (cx - dist, cy),      # Left
            (cx + dist, cy),      # Right
            (cx, cy + dist)       # Bottom
        ]
    # ... (Rest of layout logic: grid, circular, linear) ...
    elif layout_type == "grid":
        grid_w, grid_h = VIDEO_W * 0.7, VIDEO_H * 0.4
        sx, sy = (VIDEO_W - grid_w)/2, VIDEO_H * 0.2
        cw, ch = grid_w/2, grid_h/2
        for i in range(4):
            r, c = divmod(i, 2)
            positions.append((sx + c*cw + cw/2, sy + r*ch + ch/2))
            
    elif layout_type == "circular":
        cx, cy = VIDEO_W/2, VIDEO_H * 0.4
        rad = VIDEO_W * 0.25
        step = 360 / len(icons)
        for i in range(len(icons)):
            ang = math.radians(i*step - 90)
            positions.append((cx + rad*math.cos(ang), cy + rad*math.sin(ang)))
            
    else: # Linear (Default)
        sp = VIDEO_W / (len(icons) + 1)
        y = VIDEO_H * 0.4
        for i in range(len(icons)): positions.append((sp*(i+1), y))

    # Render Icons
    icon_sz = 100
    lbl_font = load_font(font_path, 28)
    
    for i, name in enumerate(icons):
        if i >= len(positions): break
        px, py = positions[i]
        
        # Icon Background Circle
        bg_r = icon_sz / 2 + 15
        draw.ellipse([px - bg_r, py - bg_r, px + bg_r, py + bg_r], fill=(0,0,0,160))
        
        if name in icon_svg:
            try:
                buf = io.BytesIO()
                cairosvg.svg2png(bytestring=icon_svg[name], write_to=buf, output_height=icon_sz)
                buf.seek(0)
                img = Image.open(buf).convert("RGBA")
                
                # Tint White
                data = np.array(img)
                data[..., :-1][data[..., 3] > 0] = (255, 255, 255)
                img = Image.fromarray(data)
                
                canvas.paste(img, (int(px-icon_sz/2), int(py-icon_sz/2)), img)
            except: pass
        
        # Label
        draw.text((px, py + bg_r + 20), name.capitalize(), font=lbl_font, fill="white", stroke_width=2, stroke_fill="black", anchor="mm")

    # Bottom Text Box
    txt_h = VIDEO_H * 0.25
    draw.rectangle([0, VIDEO_H - txt_h - 20, VIDEO_W, VIDEO_H-20], fill=(0,0,0,200))
    
    txt = story_theme['cta_text']
    t_font = load_font(font_path, 50)
    lines = utils.wrap_text_pil(txt, t_font, VIDEO_W * 0.9)
    
    cy = VIDEO_H - txt_h + 10
    for line in lines:
        draw.text((VIDEO_W/2, cy), line, font=t_font, fill="white", anchor="mm")
        cy += t_font.size * 1.3

    return ImageClip(np.array(canvas)).set_duration(duration)

# Exports for Video Renderer
def render_cta_slide_grid(slide, st, svg, th, dur, sz): return _render_cta_common(slide, st, svg, th, dur, sz, "grid")
def render_cta_slide_linear(slide, st, svg, th, dur, sz): return _render_cta_common(slide, st, svg, th, dur, sz, "linear")
def render_cta_slide_circular(slide, st, svg, th, dur, sz): return _render_cta_common(slide, st, svg, th, dur, sz, "circular")
def render_cta_slide_diamond(slide, st, svg, th, dur, sz): return _render_cta_common(slide, st, svg, th, dur, sz, "diamond")

# --- 4. OTHER RENDERERS ---

def render_chart_slide(slide_info, size, duration):
    path = slide_info.get('path')
    if path and os.path.exists(path):
        img = Image.open(path).convert("RGBA")
        img.thumbnail((int(size[0]*0.95), int(size[1]*0.95)), Image.Resampling.LANCZOS)
        bg = Image.new("RGBA", size, (0,0,0,0))
        bg.paste(img, (int((size[0]-img.width)/2), int((size[1]-img.height)/2)), img)
        return [ImageClip(np.array(bg)).set_duration(duration)]
    return []

def render_news_slide(slide_info, icon_svg, theme, duration, size):
    VIDEO_W, VIDEO_H = size
    canvas = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(canvas)
    
    font = load_font(theme['font'], 70)
    lines = utils.wrap_text_pil(slide_info['text'], font, VIDEO_W * 0.8)
    y = VIDEO_H * 0.4
    for line in lines:
        draw.text((VIDEO_W/2+3, y+3), line, font=font, fill="black", anchor="mm")
        draw.text((VIDEO_W/2, y), line, font=font, fill="white", anchor="mm")
        y += 80
        
    return [ImageClip(np.array(canvas)).set_duration(duration)]

def render_summary_slide(slide_info, theme, duration, size):
    VIDEO_W, VIDEO_H = size
    canvas = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(canvas)
    
    # FIX: Use local load_font
    font = load_font(theme['font'], 60)
    lines = utils.wrap_text_pil(slide_info['text'], font, VIDEO_W * 0.8)
    y = VIDEO_H * 0.4
    for line in lines:
        draw.text((VIDEO_W/2+3, y+3), line, font=font, fill="black", anchor="mm")
        draw.text((VIDEO_W/2, y), line, font=font, fill="white", anchor="mm")
        y += 70
        
    return [ImageClip(np.array(canvas)).set_duration(duration)]