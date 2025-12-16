import os
import math
import io
import numpy as np
import cairosvg
from PIL import Image, ImageDraw
from moviepy.editor import ImageClip

from .. import config, utils
from . import core  # Imports load_font, paste_safe_logo

# --- Helper: Draw Stock Card (Grid Logic) ---
def draw_stock_card(draw, x, y, w, h, name, font_path, theme_accent, headline=None):
    radius = 20
    bg_color = (20, 20, 25, 230)
    border_color = (200, 200, 200, 80)
    
    try: draw.rounded_rectangle([x, y, x+w, y+h], radius=radius, fill=bg_color, outline=border_color, width=2)
    except AttributeError: draw.rectangle([x, y, x+w, y+h], fill=bg_color, outline=border_color, width=2)

    header_h = max(50, h * 0.20)
    font_size = 40 if w > 300 else 30
    name_font = core.load_font(font_path, font_size)
    padding = 10
    
    while name_font.getlength(name) > (w - padding*2) and font_size > 12:
        font_size -= 2
        name_font = core.load_font(font_path, font_size)
    
    draw.text((x + w/2, y + header_h/2), name, font=name_font, fill="white", anchor="mm")
    draw.line([(x + 20, y + header_h), (x + w - 20, y + header_h)], fill=theme_accent, width=3)
    
    logo_y_start = y + header_h + padding
    
    if headline:
        hl_area_h = h * 0.25
        hl_font_size = 24 if w > 300 else 18
        hl_font = core.load_font(font_path, hl_font_size)
        
        clean_hl = headline if len(headline) < 50 else headline[:47] + "..."
        lines = core.wrap_text_pil(clean_hl, hl_font, w - padding*2)
        if len(lines) > 2: lines = lines[:2]
        
        text_y = logo_y_start
        for line in lines:
            draw.text((x + w/2, text_y), line, font=hl_font, fill="#DDDDDD", anchor="mt")
            text_y += hl_font_size * 1.2
        logo_y_start += hl_area_h

    logo_h_avail = (y + h) - logo_y_start - padding
    if logo_h_avail < 0: logo_h_avail = 0
    logo_w_avail = w - (padding * 2)
    
    return x + w/2, logo_y_start + logo_h_avail/2, logo_w_avail, logo_h_avail

# --- RENDERERS ---

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
    
    title_font = core.load_font(font_path, 60)
    draw.text((VIDEO_W/2+2, VIDEO_H * 0.10+2), title_text, font=title_font, fill="black", anchor="mm")
    draw.text((VIDEO_W/2, VIDEO_H * 0.10), title_text, font=title_font, fill="white", anchor="mm")

    if story_type in ['comparison', 'news_roundup']:
        names = slide_info.get('names', [])
        logos = slide_info.get('logos', [])
        headlines = slide_info.get('headlines', [])
        
        count = len(names)
        start_y, end_y = VIDEO_H * 0.15, VIDEO_H * 0.85
        avail_h, avail_w = end_y - start_y, VIDEO_W * 0.92
        margin_x = (VIDEO_W - avail_w) / 2
        card_coords = [] 
        
        if count == 2:
            if VIDEO_W < VIDEO_H: 
                h_each = avail_h / 2.1
                card_coords = [(margin_x, start_y, avail_w, h_each), (margin_x, end_y - h_each, avail_w, h_each)]
                draw.ellipse([VIDEO_W/2 - 35, (start_y + avail_h/2) - 35, VIDEO_W/2 + 35, (start_y + avail_h/2) + 35], fill=theme['accent'], outline="white", width=3)
                draw.text((VIDEO_W/2, start_y + avail_h/2), "VS" if story_type == 'comparison' else "&", font=core.load_font(font_path, 35), fill="white", anchor="mm")
            else:
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

        for i, (cx, cy, cw, ch) in enumerate(card_coords):
            if i < len(names):
                hl = headlines[i] if i < len(headlines) and headlines else None
                lcx, lcy, lw, lh = draw_stock_card(draw, cx, cy, cw, ch, names[i], font_path, theme['accent'], headline=hl)
                if i < len(logos) and logos[i]:
                    core.paste_safe_logo(canvas, logos[i], lcx, lcy, lw, lh)

    else:
        logo = assets.get('logo')
        if logo:
            hero_w = int(VIDEO_W * 0.35)
            hero_h = int(VIDEO_W * 0.35)
            cx = VIDEO_W / 2
            cy = VIDEO_H * 0.30
            core.paste_safe_logo(canvas, logo, cx, cy, hero_w, hero_h)

        comp_name = slide_info.get('text', '')
        name_size = 80
        comp_font = core.load_font(font_path, name_size)
        max_width = VIDEO_W * 0.95
        while name_size > 30:
            try: w = comp_font.getlength(comp_name)
            except: w = 100
            if w < max_width: break
            name_size -= 5
            comp_font = core.load_font(font_path, name_size)
            
        text_y = VIDEO_H * 0.60
        draw.text((VIDEO_W/2+3, text_y+3), comp_name, font=comp_font, fill="black", anchor="mm")
        draw.text((VIDEO_W/2, text_y), comp_name, font=comp_font, fill=theme['accent'], stroke_width=2, stroke_fill="black", anchor="mm")

    return ImageClip(np.array(canvas)).set_duration(duration)

def render_glass_news_slide(slide_info, theme, duration, size):
    VIDEO_W, VIDEO_H = size
    font_path = theme['font']
    canvas = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(canvas)
    
    # 1. Glass Card Background (Bottom 75%)
    card_h = VIDEO_H * 0.75
    card_y = VIDEO_H - card_h - (VIDEO_H * 0.10) 
    margin = 40
    
    draw.rounded_rectangle(
        [margin, card_y, VIDEO_W - margin, card_y + card_h],
        radius=30,
        fill=(15, 15, 20, 230), 
        outline=(255, 255, 255, 60),
        width=2
    )
    
    # 2. Header Layout (Left Aligned)
    header_y = card_y + 30
    
    # Logo (Top Left)
    logo = slide_info.get('logo')
    if logo:
        # Draw logo at x=margin+30, y=header_y
        core.paste_safe_logo(canvas, logo, margin + 60, header_y + 40, 80, 80)
        text_start_x = margin + 120 # Start text after logo
    else:
        text_start_x = margin + 30 # No logo, start text earlier
    
    # Company Name (Left Aligned)
    company_name = slide_info.get('company', '')
    name_size = 45
    name_font = core.load_font(font_path, name_size)
    
    # Shrink to fit width (leaving room for date on right)
    max_name_w = (VIDEO_W - margin*2) - 150 - (text_start_x - margin)
    
    while name_font.getlength(company_name) > max_name_w and name_size > 25:
        name_size -= 2
        name_font = core.load_font(font_path, name_size)
        
    draw.text((text_start_x, header_y + 40), company_name, font=name_font, fill="white", anchor="lm")
    
    # Date (Top Right, Right Aligned)
    published_dt = slide_info.get('published')
    if published_dt:
        try: date_text = published_dt.strftime("%b %d") 
        except: date_text = ""
        
        if date_text:
            time_font = core.load_font(font_path, 28)
            draw.text((VIDEO_W - margin - 30, header_y + 40), date_text, font=time_font, fill="#AAAAAA", anchor="rm")

    # Divider Line
    draw.line([(margin + 20, header_y + 90), (VIDEO_W - margin - 20, header_y + 90)], fill=theme['accent'], width=2)
    
    # 3. Content Area
    content_y_start = header_y + 110
    
    # Hero Image Logic (Upscale attempt)
    news_image_path = slide_info.get('news_image_path')
    has_image = False
    
    if news_image_path and os.path.exists(news_image_path):
        try:
            n_img = Image.open(news_image_path).convert("RGBA")
            
            # Target Dimensions
            target_w = VIDEO_W - (margin * 2) - 40
            target_h = 350
            
            # Crop/Resize Logic (Aspect Fill)
            img_ratio = n_img.width / n_img.height
            target_ratio = target_w / target_h
            
            if img_ratio > target_ratio:
                new_h = target_h
                new_w = int(target_h * img_ratio)
            else:
                new_w = target_w
                new_h = int(target_w / img_ratio)
                
            n_img = n_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Center Crop
            left = (new_w - target_w)/2
            top = (new_h - target_h)/2
            n_img = n_img.crop((left, top, left + target_w, top + target_h))
            
            # Rounded Corners Mask
            mask = Image.new("L", (target_w, target_h), 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.rounded_rectangle([0,0,target_w,target_h], radius=15, fill=255)
            
            final_img = Image.new("RGBA", (target_w, target_h), (0,0,0,0))
            final_img.paste(n_img, (0,0), mask=mask)
            
            # Paste onto canvas
            canvas.paste(final_img, (margin + 20, int(content_y_start)), final_img)
            
            content_y_start += target_h + 30
            has_image = True
            
        except Exception as e: 
            print(f"      - ⚠️ Image render error: {e}")

    # Headline Text (Left Aligned)
    headline = slide_info.get('text', '')
    
    # Adjust font size based on image presence
    hl_font_size = 40 if has_image else 55
    hl_font = core.load_font(font_path, hl_font_size)
    
    # Wrap text
    lines = core.wrap_text_pil(headline, hl_font, (VIDEO_W - margin*2) - 40)
    max_lines = 4 if has_image else 7
    if len(lines) > max_lines: lines = lines[:max_lines]
    
    text_y = content_y_start
    last_text_y = text_y
    
    for line in lines:
        # Draw Left Aligned (anchor="lt")
        draw.text((margin + 20, text_y), line, font=hl_font, fill="white", anchor="lt")
        text_y += hl_font_size * 1.3
        last_text_y = text_y

    # Source Attribution (Bottom Left)
    source = slide_info.get('source', '')
    if source:
        source_y = last_text_y + 20
        # Clamp to bottom if needed
        bottom_limit = card_y + card_h - 40
        if source_y > bottom_limit: source_y = bottom_limit
            
        draw.text((margin + 20, source_y), f"- Source: {source}", font=core.load_font(font_path, 20), fill="#888888", anchor="lm")
        
    return ImageClip(np.array(canvas)).set_duration(duration)


def render_sector_slide(slide_info, theme, duration, size):
    VIDEO_W, VIDEO_H = size
    font_path = theme['font']
    canvas = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(canvas)
    parts = slide_info['text'].split('\n'); parts = [p for p in parts if p.strip()]
    mcap = parts[1] if len(parts) > 1 else "N/A"
    sector = parts[3] if len(parts) > 3 else (parts[2] if len(parts) > 2 else "N/A")
    
    box_w = VIDEO_W * 0.9; box_h = VIDEO_H * 0.6
    bx = (VIDEO_W - box_w) / 2
    by = (VIDEO_H - box_h) / 2 - 50
    
    draw.rectangle([bx, by, bx + box_w, by + box_h], fill=(0, 0, 0, 180), outline="white", width=2)
    center_x = VIDEO_W / 2; lbl_font = core.load_font(font_path, 45)
    max_text_width = box_w * 0.9; mcap_size = 90; val_font = core.load_font(font_path, mcap_size)
    while mcap_size > 40:
        w = val_font.getlength(mcap) if hasattr(val_font, 'getlength') else val_font.getmask(mcap).getbbox()[2]
        if w < max_text_width: break
        mcap_size -= 5; val_font = core.load_font(font_path, mcap_size)
        
    y_cursor = by + (box_h * 0.25)
    draw.text((center_x, y_cursor - 50), "MARKET CAP", font=lbl_font, fill="#AAAAAA", anchor="mm")
    draw.text((center_x+3, y_cursor+3), mcap, font=val_font, fill="black", anchor="mm")
    draw.text((center_x, y_cursor), mcap, font=val_font, fill=theme['accent'], anchor="mm")
    line_y = by + (box_h * 0.5); draw.line([(bx + 40, line_y), (bx + box_w - 40, line_y)], fill="white", width=2)
    
    sector_size = 60; sec_font = core.load_font(font_path, sector_size)
    while sector_size > 30:
        w = sec_font.getlength(sector) if hasattr(sec_font, 'getlength') else sec_font.getmask(sector).getbbox()[2]
        if w < max_text_width: break
        sector_size -= 4; sec_font = core.load_font(font_path, sector_size)
        
    y_cursor = by + (box_h * 0.75)
    draw.text((center_x, y_cursor - 40), "SECTOR", font=lbl_font, fill="#AAAAAA", anchor="mm")
    draw.text((center_x+2, y_cursor+2), sector, font=sec_font, fill="black", anchor="mm")
    draw.text((center_x, y_cursor + 10), sector, font=sec_font, fill="white", anchor="mm")
    return ImageClip(np.array(canvas)).set_duration(duration)

def render_management_slide(slide_info, theme, duration, size):
    VIDEO_W, VIDEO_H = size; font_path = theme['font']
    canvas = Image.new("RGBA", size, (0,0,0,0)); draw = ImageDraw.Draw(canvas)
    
    box_w, box_h = VIDEO_W * 0.85, VIDEO_H * 0.5
    bx = (VIDEO_W - box_w)/2
    by = (VIDEO_H - box_h)/2 - 50
    
    draw.rectangle([bx, by, bx+box_w, by+box_h], fill=(0,0,0,160), outline=theme['accent'], width=3)
    parts = [p.strip() for p in slide_info['text'].split('\n') if p.strip()]
    name = parts[1] if len(parts) > 1 else "N/A"
    lbl_font = core.load_font(font_path, 45)
    draw.rectangle([bx, by, bx+box_w, by+80], fill=theme['accent'])
    draw.text((VIDEO_W/2, by+40), "LEADERSHIP", font=lbl_font, fill="white", anchor="mm")
    cx, cy = VIDEO_W/2, by + 180; r = 50
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline="white", width=3)
    draw.ellipse([cx-20, cy-25, cx+20, cy+15], fill="white")
    draw.pieslice([cx-35, cy+10, cx+35, cy+80], 180, 360, fill="white")
    nm_font = core.load_font(font_path, 65); name_lines = core.wrap_text_pil(name, nm_font, box_w * 0.9)
    text_y = cy + 100
    for line in name_lines:
        draw.text((VIDEO_W/2, text_y), line, font=nm_font, fill="white", anchor="mm"); text_y += 70
    draw.text((VIDEO_W/2, text_y + 20), "Chief Executive Officer", font=lbl_font, fill="#aaaaaa", anchor="mm")
    return ImageClip(np.array(canvas)).set_duration(duration)

def render_news_slide(slide_info, icon_svg, theme, duration, size):
    VIDEO_W, VIDEO_H = size
    canvas = Image.new("RGBA", size, (0,0,0,0)); draw = ImageDraw.Draw(canvas)
    font = core.load_font(theme['font'], 70)
    lines = core.wrap_text_pil(slide_info['text'], font, VIDEO_W * 0.8)
    
    y = VIDEO_H * 0.35
    for line in lines:
        draw.text((VIDEO_W/2+3, y+3), line, font=font, fill="black", anchor="mm")
        draw.text((VIDEO_W/2, y), line, font=font, fill="white", anchor="mm")
        y += 80
        
    source = slide_info.get('source', '')
    if source:
        source_y = VIDEO_H * 0.80 
        draw.text((VIDEO_W/2, source_y), f"- Source: {source}", font=core.load_font(theme['font'], 20), fill="#CCCCCC", anchor="mm")

    return [ImageClip(np.array(canvas)).set_duration(duration)]

def render_summary_slide(slide_info, theme, duration, size):
    VIDEO_W, VIDEO_H = size
    canvas = Image.new("RGBA", size, (0,0,0,0)); draw = ImageDraw.Draw(canvas)
    font = core.load_font(theme['font'], 60)
    lines = core.wrap_text_pil(slide_info['text'], font, VIDEO_W * 0.8)
    
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

def _render_cta_common(slide_info, story_type, icon_svg, theme, duration, size, layout_type):
    VIDEO_W, VIDEO_H = size
    font_path = theme['font']
    story_theme = config.STORY_THEMES.get(story_type, config.STORY_THEMES['news'])
    
    canvas = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(canvas)
    
    # 1. Prepare Icons
    icons = story_theme['cta_icons'][:]
    
    # Logic: Ensure unique and correct icons
    if story_type == 'comparison':
        # Comparison prefers 'share' and 'vote/comment'
        desired_order = ['share', 'comment', 'like', 'subscribe']
        icons = [i for i in desired_order if i in config.ICONS]
    
    # Ensure we have at most 4
    icons = icons[:4]
    
    # 2. Calculate Positions based on Layout
    positions = []
    center_y = VIDEO_H * 0.45  # Moved down slightly for better centering
    center_x = VIDEO_W / 2
    
    if layout_type == "diamond":
        # Diamond: Top, Left, Right, Bottom
        # Works best with 4. If 3, we omit bottom.
        radius_x = VIDEO_W * 0.25
        radius_y = VIDEO_W * 0.25 # Keep circular aspect or adapt
        
        positions = [
            (center_x, center_y - radius_y), # Top
            (center_x - radius_x, center_y), # Left
            (center_x + radius_x, center_y), # Right
            (center_x, center_y + radius_y)  # Bottom
        ]
        
    elif layout_type == "grid":
        # 2x2 Grid
        spacing_x = VIDEO_W * 0.35
        spacing_y = VIDEO_W * 0.35
        start_x = center_x - (spacing_x / 2)
        start_y = center_y - (spacing_y / 2)
        
        positions = [
            (start_x, start_y),             # Top Left
            (start_x + spacing_x, start_y), # Top Right
            (start_x, start_y + spacing_y), # Bot Left
            (start_x + spacing_x, start_y + spacing_y) # Bot Right
        ]
        
    elif layout_type == "circular":
        # Icons in a circle
        radius = VIDEO_W * 0.30
        count = len(icons)
        if count > 0:
            step = 360 / count
            for i in range(count):
                # Start from top (-90 deg)
                angle_rad = math.radians(i * step - 90)
                px = center_x + radius * math.cos(angle_rad)
                py = center_y + radius * math.sin(angle_rad)
                positions.append((px, py))
                
    else: # Linear (Default)
        # Horizontal Row
        count = len(icons)
        total_width = VIDEO_W * 0.8
        spacing = total_width / (count + 1)
        start_x = (VIDEO_W - total_width) / 2
        
        for i in range(count):
            px = start_x + spacing * (i + 1)
            positions.append((px, center_y))

    # 3. Draw Icons
    icon_sz = 100
    lbl_font = core.load_font(font_path, 28)
    
    for i, name in enumerate(icons):
        if i >= len(positions): break
        
        px, py = positions[i]
        
        # Background Circle
        bg_r = icon_sz / 2 + 20
        draw.ellipse([px - bg_r, py - bg_r, px + bg_r, py + bg_r], fill=(0,0,0,180))
        
        # Icon SVG -> PNG
        if name in icon_svg:
            try:
                buf = io.BytesIO()
                cairosvg.svg2png(bytestring=icon_svg[name], write_to=buf, output_height=icon_sz)
                buf.seek(0)
                img = Image.open(buf).convert("RGBA")
                
                # Recolor to White
                data = np.array(img)
                # Replace non-transparent pixels with White
                r, g, b, a = data.T
                white_areas = (a > 0)
                data[..., :-1][white_areas.T] = (255, 255, 255)
                img = Image.fromarray(data)
                
                canvas.paste(img, (int(px-icon_sz/2), int(py-icon_sz/2)), img)
            except Exception as e:
                print(f"Icon render error {name}: {e}")
        
        # Label
        label_text = name.capitalize()
        # Draw text below icon
        draw.text((px, py + bg_r + 15), label_text, font=lbl_font, fill="white", stroke_width=2, stroke_fill="black", anchor="mt")

    # 4. CTA Text Box (Bottom)
    txt_h = VIDEO_H * 0.20
    draw.rectangle([0, VIDEO_H - txt_h, VIDEO_W, VIDEO_H], fill=(0,0,0,220))
    
    cta_text = story_theme['cta_text']
    target_font_size = 45
    t_font = core.load_font(font_path, target_font_size)
    
    lines = core.wrap_text_pil(cta_text, t_font, VIDEO_W * 0.9)
    cy = VIDEO_H - (txt_h / 2)
    
    # Adjust for multi-line
    total_text_h = len(lines) * target_font_size * 1.3
    start_text_y = cy - (total_text_h / 2) + 10 # Slight offset
    
    for line in lines:
        draw.text((VIDEO_W/2, start_text_y), line, font=t_font, fill="white", anchor="mm")
        start_text_y += target_font_size * 1.3
        
    return ImageClip(np.array(canvas)).set_duration(duration)

def render_cta_slide_grid(s,st,v,t,d,z): return _render_cta_common(s,st,v,t,d,z,'grid')
def render_cta_slide_linear(s,st,v,t,d,z): return _render_cta_common(s,st,v,t,d,z,'linear')
def render_cta_slide_circular(s,st,v,t,d,z): return _render_cta_common(s,st,v,t,d,z,'circular')
def render_cta_slide_diamond(s,st,v,t,d,z): return _render_cta_common(s,st,v,t,d,z,'diamond')
