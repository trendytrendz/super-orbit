# ai_art_director/visuals/core.py

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import os
from .. import config

# --- Font Loading ---
def load_font(path, size):
    """
    Robust font loader that handles Linux/Codespaces/Mac paths.
    Prioritizes: 1. Exact Path -> 2. Linux System -> 3. Mac/Win System -> 4. Bitmap Default
    """
    # 1. Try specific asset path (Check existence first)
    if path and os.path.exists(path):
        try: 
            return ImageFont.truetype(str(path), size)
        except Exception as e:
            print(f"      ⚠️  Font load failed for {path}: {e}")
            pass 
        
    # 2. Try Standard Linux Fonts (Codespaces/Docker)
    linux_fallbacks = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "DejaVuSans.ttf", 
        "LiberationSans-Regular.ttf",
        "FreeSans.ttf"
    ]
    
    for font_name in linux_fallbacks:
        try:
            return ImageFont.truetype(font_name, size)
        except (OSError, IOError):
            continue

    # 3. Try System Arial (Windows/Mac)
    try: 
        return ImageFont.truetype("Arial", size)
    except (OSError, IOError):
        pass

    # 4. Total Failure (Return default bitmap)
    # print(f"      ⚠️  WARNING: Using default bitmap font (Tiny).")
    return ImageFont.load_default()

# --- Text Utils ---
def wrap_text_pil(text, font, max_width):
    if not text: return []
    words = text.split()
    lines, current_line = [], []
    for word in words:
        test_line = ' '.join(current_line + [word])
        w = font.getlength(test_line) if hasattr(font, 'getlength') else font.getmask(test_line).getbbox()[2]
        if w <= max_width: current_line.append(word)
        else:
            if current_line: lines.append(' '.join(current_line))
            current_line = [word]
    if current_line: lines.append(' '.join(current_line))
    return lines

# --- Logo Logic ---
def paste_safe_logo(canvas, logo, cx, cy, max_w, max_h):
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
        target_icon_h = badge_size - (padding * 2)

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

# --- Image Effects ---
def create_blurred_image(image_path, output_path, blur_radius=15):
    """Creates a blurred version of an image for backgrounds."""
    try:
        if not image_path or not os.path.exists(image_path):
            return None
            
        with Image.open(image_path) as img:
            blurred = img.convert('RGB').filter(ImageFilter.GaussianBlur(blur_radius))
            blurred.save(output_path)
            return output_path
    except Exception as e: 
        print(f"      - ⚠️ Blur Error: {e}")
        return None