# visual_elements.py
# v20.1.8
import os
import random
import numpy as np
import math
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import cairosvg
import io
from moviepy.editor import ImageClip, CompositeVideoClip, TextClip, ColorClip, concatenate_videoclips

import config
import utils

def pop_in_effect(clip, start_time, anim_duration=0.4):
    return clip.set_start(start_time).set_duration(anim_duration).resize(lambda t: 1 + 0.2 * (1 - 2*abs(0.5-t/anim_duration)))

def slide_in_from(clip, start_time, anim_duration=0.5, direction='left', size=(1,1)):
    w, h = size; pos_map = { 'left': lambda t: (w * (t/anim_duration - 1), 'center'), 'right': lambda t: (w * (1 - t/anim_duration), 'center'), 'top': lambda t: ('center', h * (t/anim_duration - 1)), 'bottom': lambda t: ('center', h * (1 - t/anim_duration)) }; return clip.set_start(start_time).set_duration(anim_duration).set_position(pos_map[direction])

def apply_random_animation(clip, start_time, slide_duration, size):
    hold_before_anim = 0.1
    if slide_duration <= hold_before_anim: return clip.set_duration(slide_duration).set_start(start_time)
    initial_hold = clip.copy().set_duration(hold_before_anim).set_start(start_time)
    remaining_duration = slide_duration - hold_before_anim
    anim_duration = min(0.6, remaining_duration * 0.5)
    animation_style = random.choice(['pop', 'slide_left', 'slide_top']); print(f"      - Applying animation: {animation_style}")
    if animation_style == 'pop': animation = pop_in_effect(clip, start_time + hold_before_anim, anim_duration)
    elif animation_style == 'slide_left': animation = slide_in_from(clip, start_time + hold_before_anim, anim_duration, 'left', size)
    else: animation = slide_in_from(clip, start_time + hold_before_anim, anim_duration, 'top', size)
    hold_after_anim = remaining_duration - anim_duration
    if hold_after_anim > 0.01:
        final_hold = clip.copy().set_duration(hold_after_anim).set_start(start_time + hold_before_anim + anim_duration)
        return CompositeVideoClip([initial_hold, animation, final_hold])
    return CompositeVideoClip([initial_hold, animation.set_duration(remaining_duration)])

# (All other functions before render_intro_slide are unchanged)
def create_pan_zoom_clip(duration, bg_path, size):
    bg_color_tuple = tuple(int(config.BG_COLOR.lstrip('#')[i:i+2], 16) for i in (0, 2, 4));
    if not bg_path: return ColorClip(size=size, color=bg_color_tuple, duration=duration)
    try:
        zoom_margin = 1.2; img = Image.open(bg_path); target_aspect = size[0] / size[1]; img_aspect = img.width / img.height
        if img_aspect > target_aspect: new_width = int(target_aspect * img.height); offset = (img.width - new_width) / 2; img = img.crop((offset, 0, img.width - offset, img.height))
        else: new_height = int(img.width / target_aspect); offset = (img.height - new_height) / 2; img = img.crop((0, offset, img.width, img.height - offset))
        resized_w, resized_h = int(size[0] * zoom_margin), int(size[1] * zoom_margin); x_start, y_start = 0, 0; x_end = size[0] - resized_w; y_end = size[1] - resized_h
        pan_path = random.choice([((x_start, y_start), (x_end, y_end)), ((x_end, y_start), (x_start, y_end)), ((x_start, y_end), (x_end, y_start)), ((x_end, y_end), (x_start, y_start))])
        return ImageClip(np.array(img)).set_duration(duration).resize((resized_w, resized_h)).set_position(lambda t: (pan_path[0][0] + (pan_path[1][0] - pan_path[0][0]) * t / duration, pan_path[0][1] + (pan_path[1][1] - pan_path[0][1]) * t / duration))
    except Exception as e: print(f"  - Warning: Could not create pan/zoom BG, using static color. Error: {e}"); return ColorClip(size=size, color=bg_color_tuple, duration=duration)
def create_blurred_image(image_path, output_path, blur_radius=15):
    try:
        with Image.open(image_path) as img: blurred_img = img.convert('RGB').filter(ImageFilter.GaussianBlur(blur_radius)); blurred_img.save(output_path, 'png'); return output_path
    except Exception as e: print(f"    - WARNING: Could not blur image {image_path}. Error: {e}"); return None
def draw_gradient_text(draw, text, font, position, color1, color2):
    x, y = position; lines = utils.wrap_text_pil(text, font, 10000)
    line_heights = [draw.textbbox((0, 0), line, font=font)[3] for line in lines]; total_text_height = sum(line_heights) + (len(lines) - 1) * (font.size * 0.2) if lines else 0
    if total_text_height == 0: return
    current_y = y
    for i, line in enumerate(lines):
        line_bbox = draw.textbbox((0, 0), line, font=font); line_width, line_height = line_bbox[2], line_bbox[3]; text_mask = Image.new('L', (line_width, line_height)); mask_draw = ImageDraw.Draw(text_mask); mask_draw.text((0, 0), line, font=font, fill=255)
        start_ratio = (current_y - y) / total_text_height if total_text_height > 0 else 0; end_ratio = (current_y + line_height - y) / total_text_height if total_text_height > 0 else 1
        c1 = np.array(Image.new('RGB', (1,1), color1).getpixel((0,0))); c2 = np.array(Image.new('RGB', (1,1), color2).getpixel((0,0)))
        line_c1 = tuple(int(c) for c in (c1 + (c2 - c1) * start_ratio)); line_c2 = tuple(int(c) for c in (c1 + (c2 - c1) * end_ratio))
        gradient_img = utils.create_gradient_image((line_width, line_height), f"rgb{line_c1}", f"rgb{line_c2}", 'vertical')
        draw.text((x + 3, current_y + 3), line, font=font, fill="#00000088"); draw._image.paste(gradient_img, (int(x), int(current_y)), text_mask); current_y += line_heights[i] * 1.2
def create_slide_content(content_elements, size, font_path, theme):
    fg_img = Image.new("RGBA", size, (0,0,0,0)); draw = ImageDraw.Draw(fg_img)
    for element in content_elements:
        if element['type'] == 'text':
            font = utils.get_optimal_font_size(element['text'], element.get('initial_fontsize', 70), element.get('box', size)[0], element.get('box', size)[1], font_path)
            lines = utils.wrap_text_pil(element['text'], font, element.get('box', size)[0]); line_heights = [draw.textbbox((0,0), line, font=font)[3] for line in lines]; total_text_height = sum(line_heights) + (len(lines) - 1) * (font.size * 0.2)
            y_pos = element['position'][1] - total_text_height / 2
            if element.get('is_title', False):
                 for i, line in enumerate(lines):
                    line_bbox = draw.textbbox((0, 0), line, font=font); line_width = line_bbox[2]; x_pos = element['position'][0] - line_width / 2
                    draw_gradient_text(draw, line, font, (x_pos, y_pos), theme['accent'], theme.get('gradient_end', theme['accent'])); y_pos += line_heights[i] * 1.2
            else:
                 for i, line in enumerate(lines):
                    line_width = draw.textlength(line, font=font); x_pos = element['position'][0] - line_width / 2
                    draw.text((x_pos + 3, y_pos + 3), line, font=font, fill="#00000088"); draw.text((x_pos, y_pos), line, font=font, fill=element.get('color', theme['text'])); y_pos += line_heights[i] * 1.2
        elif element['type'] == 'image':
            img_to_paste_file = element['data'] if 'data' in element and isinstance(element['data'], Image.Image) else Image.open(element['path']).convert("RGBA")
            if img_to_paste_file: img_to_paste = img_to_paste_file.copy(); img_to_paste.thumbnail(element.get('size', (100, 100)), Image.Resampling.LANCZOS); paste_pos = (int(element['position'][0] - img_to_paste.width / 2), int(element['position'][1] - img_to_paste.height / 2)); fg_img.paste(img_to_paste, paste_pos, img_to_paste)
    return fg_img
def create_spotlight_background(size, accent_color):
    W, H = size; center = (W / 2, H / 2); max_radius = np.sqrt((W/2)**2 + (H/2)**2); img = Image.new('RGB', (W, H), color = config.BG_COLOR); draw = ImageDraw.Draw(img, 'RGBA')
    for i in range(int(max_radius), 0, -5): radius_norm = i / max_radius; alpha = int(255 * (1 - radius_norm)**3 * 0.3); r, g, b = Image.new('RGB', (1,1), accent_color).getpixel((0,0)); draw.ellipse((center[0]-i, center[1]-i, center[0]+i, center[1]+i), fill=(r, g, b, alpha))
    return img
def create_vs_background(size, accent_color, font_path):
    W, H = size; img = Image.new('RGB', (W, H), config.BG_COLOR); draw = ImageDraw.Draw(img)
    for i in range(H): ratio = i / H; color_val = int(12 + ratio * 20); draw.line([(0, i), (W, i)], fill=(color_val, color_val, int(color_val*1.2)))
    vs_font = ImageFont.truetype(font_path, int(H * 0.5)); r, g, b = Image.new('RGB', (1,1), accent_color).getpixel((0,0)); text_color = (r, g, b, 50)
    txt_img = Image.new('RGBA', size); txt_draw = ImageDraw.Draw(txt_img); txt_draw.text((W/2, H/2), "VS", font=vs_font, fill=text_color, anchor="mm"); img = Image.alpha_composite(img.convert('RGBA'), txt_img).convert('RGB'); return img
def create_typing_text_clip(text, duration, font, initial_fontsize, box_size, pos, color):
    font_obj = utils.get_optimal_font_size(text, initial_fontsize, box_size[0], box_size[1], font); wrapped_lines = utils.wrap_text_pil(text, font_obj, box_size[0]); full_text_for_anim = "\n".join(wrapped_lines)
    clips = []; text_len = len(full_text_for_anim); char_duration = duration / (text_len + 1) if text_len > 0 else duration
    for i in range(1, text_len + 1): sub_text = full_text_for_anim[:i]; txt_clip = TextClip(sub_text, font=font, fontsize=font_obj.size, color=color, align='center', size=box_size, method='caption').set_duration(char_duration); clips.append(txt_clip)
    if not clips: return ColorClip(size=box_size, color=(0,0,0,0), duration=duration).set_position(pos), None
    animation = concatenate_videoclips(clips); final_frame = TextClip(full_text_for_anim, font=font, fontsize=font_obj.size, color=color, align='center', size=box_size, method='caption'); return animation.set_position(pos), final_frame.set_position(pos)

### SLIDE COMPOSITION FUNCTIONS ###

def render_intro_slide(slide_info, story_type, assets, theme, duration, size):
    VIDEO_W, VIDEO_H = size; font_path = theme['font']
    
    fg_content_elements = []
    if story_type == "comparison" and (logos_pil := [logo for logo in slide_info.get('logos', []) if logo]):
        # FIX (Feedback #3): Dynamic layout for 2, 3, or 4 companies.
        num_companies = len(logos_pil)
        
        # Define layout parameters based on number of companies
        if num_companies <= 3:
            y_pos_logo, y_pos_text = VIDEO_H * 0.40, VIDEO_H * 0.60
            logo_max_w, logo_max_h = VIDEO_W / (num_companies + 1), VIDEO_H * 0.25
        else: # For 4 companies, use a 2x2 grid
            y_pos_logo, y_pos_text = (VIDEO_H * 0.3, VIDEO_H * 0.7), (VIDEO_H * 0.45, VIDEO_H * 0.85)
            logo_max_w, logo_max_h = VIDEO_W * 0.35, VIDEO_H * 0.2
            
        for i, logo in enumerate(logos_pil):
            logo.thumbnail((logo_max_w, logo_max_h), Image.Resampling.LANCZOS)
            
            if num_companies <= 3: # Linear layout
                x_pos = (VIDEO_W * (i + 1)) / (num_companies + 1)
                logo_y, text_y = y_pos_logo, y_pos_text
            else: # 2x2 Grid layout
                col, row = i % 2, i // 2
                x_pos = (VIDEO_W * (col + 1)) / 3
                logo_y, text_y = y_pos_logo[row], y_pos_text[row]

            fg_content_elements.append({"type": "image", "data": logo, "size": logo.size, "position": (x_pos, logo_y)})
            company_name_text = slide_info['text'].split('\nvs.\n')[i]
            fg_content_elements.append({
                "type": "text", "text": company_name_text, "position": (x_pos, text_y), 
                "box": (VIDEO_W / num_companies * 0.9, VIDEO_H * 0.15), "initial_fontsize": 50
            })
            
        main_title = config.STORY_THEMES['comparison']['intro_text']
        fg_content_elements.append({"type": "text", "text": main_title, "position": (VIDEO_W/2, VIDEO_H * 0.15), "box": (VIDEO_W*0.8, VIDEO_H*0.15), "initial_fontsize": 90, "is_title": True})

    else: # Standard intro for other types
        if slide_info.get('logo') and assets.get('logo'):
            logo = assets.get('logo'); logo.thumbnail((int(VIDEO_W * 0.8), int(VIDEO_H * 0.4)), Image.Resampling.LANCZOS)
            fg_content_elements.append({"type": "image", "data": logo, "size": logo.size, "position": (VIDEO_W/2, VIDEO_H * 0.4)})
        fg_content_elements.append({"type": "text", "text": slide_info['text'], "position": (VIDEO_W / 2, VIDEO_H * 0.75), "box": (VIDEO_W * 0.8, VIDEO_H * 0.3), "initial_fontsize": 90, "is_title": True})

    fg_img = create_slide_content(fg_content_elements, size, font_path, theme)
    return ImageClip(np.array(fg_img)).set_duration(duration)

# (The rest of the file is identical to v20.1.4, no other changes are needed)
def render_cta_slide_linear(slide_info, story_type, icon_svg, theme, duration, size):
    VIDEO_W, VIDEO_H = size; font_path = theme['font']; story_theme = config.STORY_THEMES.get(story_type, config.STORY_THEMES['news'])
    canvas = Image.new("RGBA", size, (0, 0, 0, 0)); draw = ImageDraw.Draw(canvas)
    icon_size, icon_spacing, label_font_size = 100, 80, 40
    num_icons = len(story_theme['cta_icons']); total_width = num_icons * icon_size + (num_icons - 1) * icon_spacing
    start_x, block_midpoint_y = (VIDEO_W - total_width) / 2, VIDEO_H * 0.5
    icon_y_pos, label_y_pos, main_text_y_pos = int(block_midpoint_y - icon_size / 2), int(block_midpoint_y + icon_size / 2 + 15), int(block_midpoint_y + icon_size / 2 + 75)
    main_text_font = ImageFont.truetype(font_path, 65); main_text_bbox = draw.textbbox((0,0), story_theme['cta_text'], font=main_text_font)
    draw.text(((VIDEO_W - main_text_bbox[2]) / 2, main_text_y_pos), story_theme['cta_text'], font=main_text_font, fill=theme['text'])
    label_font = ImageFont.truetype(font_path, label_font_size)
    for i, icon_name in enumerate(story_theme['cta_icons']):
        try:
            png_buffer = io.BytesIO(); cairosvg.svg2png(bytestring=icon_svg[icon_name], write_to=png_buffer, output_height=icon_size); png_buffer.seek(0)
            icon_img = Image.open(png_buffer).convert("RGBA"); icon_x_pos = int(start_x + i * (icon_size + icon_spacing))
            canvas.paste(icon_img, (icon_x_pos, icon_y_pos), icon_img)
            label_text = icon_name.capitalize(); label_bbox = draw.textbbox((0,0), label_text, font=label_font)
            draw.text((icon_x_pos + (icon_size / 2) - (label_bbox[2] / 2), label_y_pos), label_text, font=label_font, fill=theme['text'])
        except Exception as e: print(f"      - ❌ ERROR rendering CTA icon '{icon_name}': {e}")
    return ImageClip(np.array(canvas), transparent=True).set_duration(duration)
def render_cta_slide_circular(slide_info, story_type, icon_svg, theme, duration, size):
    VIDEO_W, VIDEO_H = size; font_path = theme['font']; story_theme = config.STORY_THEMES.get(story_type, config.STORY_THEMES['news'])
    canvas = Image.new("RGBA", size, (0, 0, 0, 0)); draw = ImageDraw.Draw(canvas); center_x, center_y = VIDEO_W / 2, VIDEO_H * 0.45
    radius = min(VIDEO_W, VIDEO_H) * 0.25; icon_size, label_font_size = 90, 35
    num_icons = len(story_theme['cta_icons']); angle_step = 360 / num_icons if num_icons > 0 else 0
    label_font = ImageFont.truetype(font_path, label_font_size)
    for i, icon_name in enumerate(story_theme['cta_icons']):
        try:
            angle = math.radians(i * angle_step - 90)
            icon_x, icon_y = int(center_x + radius * math.cos(angle) - icon_size / 2), int(center_y + radius * math.sin(angle) - icon_size / 2)
            png_buffer = io.BytesIO(); cairosvg.svg2png(bytestring=icon_svg[icon_name], write_to=png_buffer, output_height=icon_size); png_buffer.seek(0)
            icon_img = Image.open(png_buffer).convert("RGBA"); canvas.paste(icon_img, (icon_x, icon_y), icon_img)
            label_text = icon_name.capitalize(); label_bbox = draw.textbbox((0,0), label_text, font=label_font)
            label_x, label_y = int(center_x + (radius + icon_size * 0.7) * math.cos(angle) - label_bbox[2] / 2), int(center_y + (radius + icon_size * 0.7) * math.sin(angle) - label_bbox[3] / 2)
            draw.text((label_x, label_y), label_text, font=label_font, fill=theme['text'])
        except Exception as e: print(f"      - ❌ ERROR rendering circular CTA icon '{icon_name}': {e}")
    main_text_font = ImageFont.truetype(font_path, 65); main_text_bbox = draw.textbbox((0,0), story_theme['cta_text'], font=main_text_font)
    draw.text(((VIDEO_W - main_text_bbox[2]) / 2, VIDEO_H * 0.8), story_theme['cta_text'], font=main_text_font, fill=theme['text'])
    return ImageClip(np.array(canvas), transparent=True).set_duration(duration)
def render_cta_slide_grid(slide_info, story_type, icon_svg, theme, duration, size):
    print("      - Rendering new grid CTA slide."); VIDEO_W, VIDEO_H = size; font_path = theme['font']; story_theme = config.STORY_THEMES.get(story_type, config.STORY_THEMES['news'])
    canvas = Image.new("RGBA", size, (0, 0, 0, 0)); draw = ImageDraw.Draw(canvas); icons = story_theme['cta_icons']; num_icons = len(icons)
    cols = 2 if num_icons <= 4 else 3; rows = math.ceil(num_icons / cols); grid_w, grid_h = VIDEO_W * 0.7, VIDEO_H * 0.5; start_x, start_y = (VIDEO_W - grid_w) / 2, VIDEO_H * 0.2
    cell_w, cell_h = grid_w / cols, grid_h / rows; icon_size = int(min(cell_w, cell_h) * 0.5); label_font = ImageFont.truetype(font_path, 30)
    for i, icon_name in enumerate(icons):
        try:
            row, col = divmod(i, cols); cell_center_x, cell_center_y = start_x + col * cell_w + cell_w / 2, start_y + row * cell_h + cell_h / 2
            icon_x, icon_y = int(cell_center_x - icon_size / 2), int(cell_center_y - icon_size / 2)
            png_buffer = io.BytesIO(); cairosvg.svg2png(bytestring=icon_svg[icon_name], write_to=png_buffer, output_height=icon_size); png_buffer.seek(0)
            icon_img = Image.open(png_buffer).convert("RGBA"); canvas.paste(icon_img, (icon_x, icon_y), icon_img)
            label_text = icon_name.capitalize(); label_bbox = draw.textbbox((0,0), label_text, font=label_font)
            draw.text((cell_center_x - label_bbox[2]/2, icon_y + icon_size + 5), label_text, font=label_font, fill=theme['text'])
        except Exception as e: print(f"      - ❌ ERROR rendering grid CTA icon '{icon_name}': {e}")
    main_text_font = ImageFont.truetype(font_path, 65); main_text_bbox = draw.textbbox((0,0), story_theme['cta_text'], font=main_text_font)
    draw.text(((VIDEO_W - main_text_bbox[2]) / 2, VIDEO_H * 0.8), story_theme['cta_text'], font=main_text_font, fill=theme['text'])
    return ImageClip(np.array(canvas), transparent=True).set_duration(duration)
def render_cta_slide_diamond(slide_info, story_type, icon_svg, theme, duration, size):
    print("      - Rendering new diamond CTA slide."); VIDEO_W, VIDEO_H = size; font_path = theme['font']; story_theme = config.STORY_THEMES.get(story_type, config.STORY_THEMES['news'])
    canvas = Image.new("RGBA", size, (0, 0, 0, 0)); draw = ImageDraw.Draw(canvas)
    icons = story_theme['cta_icons'][:4]; center_x, center_y = VIDEO_W / 2, VIDEO_H * 0.45; radius_x, radius_y = VIDEO_W * 0.3, VIDEO_H * 0.2; icon_size = 90
    positions = [(center_x, center_y - radius_y), (center_x + radius_x, center_y), (center_x, center_y + radius_y), (center_x - radius_x, center_y)]
    label_font = ImageFont.truetype(font_path, 35)
    for i, icon_name in enumerate(icons):
        try:
            pos_x, pos_y = positions[i]; icon_x, icon_y = int(pos_x - icon_size / 2), int(pos_y - icon_size / 2)
            png_buffer = io.BytesIO(); cairosvg.svg2png(bytestring=icon_svg[icon_name], write_to=png_buffer, output_height=icon_size); png_buffer.seek(0)
            icon_img = Image.open(png_buffer).convert("RGBA"); canvas.paste(icon_img, (icon_x, icon_y), icon_img)
            label_text = icon_name.capitalize(); label_bbox = draw.textbbox((0,0), label_text, font=label_font)
            draw.text((pos_x - label_bbox[2]/2, pos_y + icon_size * 0.6), label_text, font=label_font, fill=theme['text'])
        except Exception as e: print(f"      - ❌ ERROR rendering diamond CTA icon '{icon_name}': {e}")
    main_text_font = ImageFont.truetype(font_path, 65); main_text_bbox = draw.textbbox((0,0), story_theme['cta_text'], font=main_text_font)
    draw.text(((VIDEO_W - main_text_bbox[2]) / 2, VIDEO_H * 0.8), story_theme['cta_text'], font=main_text_font, fill=theme['text'])
    return ImageClip(np.array(canvas), transparent=True).set_duration(duration)
def render_news_slide(slide_info, icon_svg, theme, duration, size):
    VIDEO_W, VIDEO_H = size; font_path = theme['font']; slide_composites = []
    png_buffer = io.BytesIO(); cairosvg.svg2png(bytestring=icon_svg[slide_info['icon']], write_to=png_buffer, output_height=60); png_buffer.seek(0)
    icon_array = np.array(Image.open(png_buffer)); icon_clip = ImageClip(icon_array, transparent=True).set_duration(duration).set_position((VIDEO_W * 0.1, VIDEO_H * 0.15))
    typing_duration = min(3.5, duration * 0.7); animation, final_text = create_typing_text_clip(slide_info['text'], typing_duration, font_path, 108, (VIDEO_W * 0.85, VIDEO_H * 0.8), ('center', 'center'), theme['accent'])
    hold_duration = duration - animation.duration
    text_element = concatenate_videoclips([animation, final_text.set_duration(hold_duration)]) if hold_duration > 0 and final_text else animation.set_duration(duration)
    slide_composites.append(text_element); slide_composites.append(icon_clip); return slide_composites
def render_summary_slide(slide_info, theme, duration, size):
    VIDEO_W, VIDEO_H = size; font_path = theme['font']
    is_title_slide = slide_info.get('is_title', False); font_size = 110 if is_title_slide else 60
    content = [{"type": "text", "text": slide_info['text'], "position": (VIDEO_W / 2, VIDEO_H / 2), "box": (VIDEO_W * 0.85, VIDEO_H * 0.8), "initial_fontsize": font_size, "is_title": is_title_slide}]
    fg_img = create_slide_content(content, size, font_path, theme); return [ImageClip(np.array(fg_img)).set_duration(duration)]
def render_chart_slide(slide_info, size, duration):
    if (path := slide_info.get('path')) and os.path.exists(path):
        with Image.open(path) as chart_img_file:
            chart_img = chart_img_file.convert("RGBA"); chart_img.thumbnail((int(size[0] * 0.95), int(size[1] * 0.95)), Image.Resampling.LANCZOS)
            fg_img = Image.new("RGBA", size, (0,0,0,0)); fg_img.paste(chart_img, ((size[0] - chart_img.width) // 2, (size[1] - chart_img.height) // 2), chart_img)
            return [ImageClip(np.array(fg_img)).set_duration(duration)]
    print(f"    - WARNING: Chart path for slide '{slide_info['key']}' not found. Skipping visuals."); return []
