# video_renderer.py
import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import cairosvg
from scipy.ndimage import gaussian_filter

from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip, CompositeAudioClip,
    concatenate_audioclips, concatenate_videoclips, TextClip, ColorClip, AudioClip
)
from moviepy.video.tools.subtitles import SubtitlesClip

import config
import utils
import content_creator

def create_blurred_image(image_path, output_path, blur_radius=15):
    try:
        with Image.open(image_path) as img:
            blurred_img = img.filter(ImageFilter.GaussianBlur(blur_radius))
            blurred_img.save(output_path)
            return output_path
    except Exception as e:
        print(f"    - WARNING: Could not blur image {image_path}. Error: {e}")
        return None

def create_chart_slide_image(chart_path, size):
    fg_img = Image.new("RGBA", size, (0,0,0,0));
    with Image.open(chart_path) as chart_img_file:
        chart_img = chart_img_file.convert("RGBA")
        chart_img.thumbnail((int(size[0] * 0.95), int(size[1] * 0.95)), Image.Resampling.LANCZOS)
        paste_x = (size[0] - chart_img.width) // 2; paste_y = (size[1] - chart_img.height) // 2
        fg_img.paste(chart_img, (paste_x, paste_y), chart_img)
    return fg_img

def create_slide_content(content_elements, size, font_path, theme):
    fg_img = Image.new("RGBA", size, (0,0,0,0)); draw = ImageDraw.Draw(fg_img)
    for element in content_elements:
        if element['type'] == 'text':
            font = utils.get_optimal_font_size(element['text'], element.get('initial_fontsize', 70), element.get('box', size)[0], element.get('box', size)[1], font_path)
            lines = utils.wrap_text_pil(element['text'], font, element.get('box', size)[0])
            line_heights = [draw.textbbox((0,0), line, font=font)[3] for line in lines]
            total_text_height = sum(line_heights) + (len(lines) - 1) * (font.size * 0.2)
            y_pos = element['position'][1] - total_text_height / 2
            for i, line in enumerate(lines):
                line_width = draw.textlength(line, font=font); x_pos = element['position'][0] - line_width / 2
                draw.text((x_pos + 3, y_pos + 3), line, font=font, fill="#00000088")
                draw.text((x_pos, y_pos), line, font=font, fill=element.get('color', theme['text'])); y_pos += line_heights[i] * 1.2
        elif element['type'] == 'image':
             with Image.open(element['path']) as img_to_paste_file:
                img_to_paste = img_to_paste_file.convert("RGBA"); img_to_paste.thumbnail(element['size'], Image.Resampling.LANCZOS)
                paste_pos = (int(element['position'][0] - img_to_paste.width / 2), int(element['position'][1] - img_to_paste.height / 2))
                fg_img.paste(img_to_paste, paste_pos, img_to_paste)
    return fg_img

# --- ROBUST TYPING ANIMATION FUNCTION ---
def create_typing_text_clip(text, duration, font, initial_fontsize, box_size, pos, color):
    """
    Creates a moviepy clip with a typing animation effect by concatenating TextClips.
    Returns the concatenated animation clip and the final static clip.
    """
    font_obj = utils.get_optimal_font_size(text, initial_fontsize, box_size[0], box_size[1], font)
    wrapped_lines = utils.wrap_text_pil(text, font_obj, box_size[0])
    full_text_for_anim = "\n".join(wrapped_lines)
    
    clips = []
    text_len = len(full_text_for_anim)
    char_duration = (duration / text_len) if text_len > 0 else duration

    # Create a clip for each character addition
    for i in range(1, text_len + 1):
        sub_text = full_text_for_anim[:i]
        txt_clip = TextClip(sub_text, font=font, fontsize=font_obj.size, color=color, align='center', size=box_size, method='caption').set_duration(char_duration)
        clips.append(txt_clip)
    
    if not clips:
        # If no text, return empty clips
        empty_clip = ColorClip(size=box_size, color=(0,0,0,0), duration=duration).set_position(pos)
        return empty_clip, empty_clip.copy().set_duration(0)

    # The final frame is a static TextClip of the full text
    final_clip = TextClip(full_text_for_anim, font=font, fontsize=font_obj.size, color=color, align='center', size=box_size, method='caption')
    
    # The animation is the concatenation of all sub-clips
    animation = concatenate_videoclips(clips).set_position(pos)
    
    return animation, final_clip.set_position(pos)

def create_pan_zoom_clip(duration, bg_path, size):
    bg_color_tuple = tuple(int(config.BG_COLOR.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    if not bg_path: return ColorClip(size=size, color=bg_color_tuple, duration=duration)
    try:
        zoom_margin = 1.2; img = Image.open(bg_path); target_aspect = size[0] / size[1]; img_aspect = img.width / img.height
        if img_aspect > target_aspect:
            new_width = int(target_aspect * img.height); offset = (img.width - new_width) / 2; img = img.crop((offset, 0, img.width - offset, img.height))
        else:
            new_height = int(img.width / target_aspect); offset = (img.height - new_height) / 2; img = img.crop((0, offset, img.width, img.height - offset))
        resized_w = int(size[0] * zoom_margin); resized_h = int(size[1] * zoom_margin)
        x_start, y_start = 0, 0; x_end = size[0] - resized_w; y_end = size[1] - resized_h
        pan_path = random.choice([((x_start, y_start), (x_end, y_end)), ((x_end, y_start), (x_start, y_end)), ((x_start, y_end), (x_end, y_start)), ((x_end, y_end), (x_start, y_start))])
        return ImageClip(np.array(img)).set_duration(duration).resize((resized_w, resized_h)).set_position(lambda t: (pan_path[0][0] + (pan_path[1][0] - pan_path[0][0]) * t / duration, pan_path[0][1] + (pan_path[1][1] - pan_path[0][1]) * t / duration))
    except Exception as e:
        print(f"  - Warning: Could not create pan/zoom BG, using static color. Error: {e}"); return ColorClip(size=size, color=bg_color_tuple, duration=duration)

# --- Main Video Rendering Function ---
def make_video(slides, audio_paths, company, nse_symbol, video_format, out_path, assets, theme, icon_svg):
    VIDEO_W, VIDEO_H = (config.VIDEO_W_LANDSCAPE, config.VIDEO_H_LANDSCAPE) if video_format == 'landscape' else (config.VIDEO_W_PORTRAIT, config.VIDEO_H_PORTRAIT)
    font_path = theme['font']; bg_images = assets.get('bg_images', [])
    
    blurred_bg_paths = {}
    for i, img_path in enumerate(bg_images):
        output_path = os.path.join(utils.get_script_dir(), "outputs", "tmp", f"bg_blurred_{i}.jpg")
        if blurred_path := create_blurred_image(img_path, output_path):
            blurred_bg_paths[img_path] = blurred_path
            
    audio_clips_timeline = []; slide_clips = []; current_time = 0.0; bg_idx = 0
    print("   -> Generating all slides and building timeline...")

    for slide_info in slides:
        key = slide_info['key']
        audio_clip = None; duration = 0
        if key in audio_paths and os.path.exists(audio_paths[key]):
            try:
                audio_clip = AudioFileClip(audio_paths[key]); audio_duration = audio_clip.duration
                padding = 1.8; duration = audio_duration + padding; duration = max(duration, 4.5)
            except Exception as e: print(f"    - WARNING: Could not read audio duration for '{key}'. Skipping. Error: {e}"); continue
        else:
            duration = config.TITLE_SLIDE_DURATION; audio_clip = AudioClip(lambda t: [0, 0], duration=duration, fps=44100)
        if duration <= 0:
            if audio_clip: audio_clip.close(); continue
        audio_clips_timeline.append(audio_clip.set_start(current_time))
        
        bg_path = bg_images[bg_idx % len(bg_images)] if bg_images else None
        final_bg_path = blurred_bg_paths.get(bg_path, bg_path) if slide_info.get('blur_bg', False) else bg_path
        bg_clip = create_pan_zoom_clip(duration, final_bg_path, (VIDEO_W, VIDEO_H))
        
        fg_clip = None
        if slide_info['type'] == 'intro':
            content = [{"type": "text", "text": slide_info['text'], "position": (VIDEO_W / 2, VIDEO_H * 0.65), "box": (VIDEO_W * 0.8, VIDEO_H * 0.4), "initial_fontsize": 90}]
            if slide_info.get('logo') and assets.get('logo'):
                logo_path = os.path.join(utils.get_script_dir(), "outputs", "tmp", "logo.png"); assets['logo'].save(logo_path)
                logo_size = (int(min(VIDEO_W, VIDEO_H) * 0.25), int(min(VIDEO_W, VIDEO_H) * 0.25))
                content.insert(0, {"type": "image", "path": logo_path, "size": logo_size, "position": (VIDEO_W/2, VIDEO_H * 0.3)})
            fg_img = create_slide_content(content, (VIDEO_W, VIDEO_H), font_path, theme); fg_clip = ImageClip(np.array(fg_img)).set_duration(duration)
        elif slide_info['type'] == 'news':
            icon_path = os.path.join(utils.get_script_dir(), "outputs", "tmp", f"{slide_info['icon']}_icon.png"); cairosvg.svg2png(bytestring=icon_svg[slide_info['icon']], write_to=icon_path, output_height=60)
            icon_clip = ImageClip(icon_path).set_duration(duration).set_position((VIDEO_W * 0.1, VIDEO_H * 0.15))

            # --- ROBUST TYPING & HOLD LOGIC ---
            typing_duration = min(3.5, duration * 0.7)
            animation, final_text = create_typing_text_clip(slide_info['text'], typing_duration, font_path, 108, (VIDEO_W * 0.85, VIDEO_H * 0.8), ('center', 'center'), theme['accent'])
            hold_duration = duration - animation.duration
            if hold_duration > 0:
                hold_clip = final_text.set_duration(hold_duration)
                text_element = concatenate_videoclips([animation, hold_clip])
            else:
                text_element = animation.set_duration(duration)
            
            fg_clip = CompositeVideoClip([text_element, icon_clip])
            # --- END ROBUST LOGIC ---

        elif slide_info['type'] == 'summary':
            is_title_slide = slide_info.get('is_title', False); font_size = 90 if is_title_slide else 60
            content = [{"type": "text", "text": slide_info['text'], "position": (VIDEO_W / 2, VIDEO_H / 2), "box": (VIDEO_W * 0.85, VIDEO_H * 0.8), "initial_fontsize": font_size}]
            fg_img = create_slide_content(content, (VIDEO_W, VIDEO_H), font_path, theme); fg_clip = ImageClip(np.array(fg_img)).set_duration(duration)
        elif slide_info['type'] == 'chart':
            if (path := slide_info.get('path')) and os.path.exists(path):
                fg_img = create_chart_slide_image(path, (VIDEO_W, VIDEO_H)); fg_clip = ImageClip(np.array(fg_img)).set_duration(duration)
            else: print(f"    - WARNING: Chart path for slide '{key}' not found. Skipping visuals."); fg_clip = ColorClip(size=(1,1), color=(0,0,0,0), duration=duration)
        elif slide_info['type'] == 'cta':
            icon_paths = {name: os.path.join(utils.get_script_dir(), "outputs", "tmp", f"icon_{name}.png") for name in ['like', 'comment', 'share']}
            for name in icon_paths.keys():
                cairosvg.svg2png(bytestring=icon_svg[name], write_to=icon_paths[name], output_height=80)
            icon_size = (80, 80); y_pos_icon = VIDEO_H * 0.45; y_pos_text = y_pos_icon + 80
            content = [{"type": "image", "path": icon_paths['like'], "size": icon_size, "position": (VIDEO_W * 0.25, y_pos_icon)}, {"type": "text", "text": "Like", "position": (VIDEO_W * 0.25, y_pos_text), "initial_fontsize": 40}, {"type": "image", "path": icon_paths['comment'], "size": icon_size, "position": (VIDEO_W * 0.5, y_pos_icon)}, {"type": "text", "text": "Comment", "position": (VIDEO_W * 0.5, y_pos_text), "initial_fontsize": 40}, {"type": "image", "path": icon_paths['share'], "size": icon_size, "position": (VIDEO_W * 0.75, y_pos_icon)}, {"type": "text", "text": "Share", "position": (VIDEO_W * 0.75, y_pos_text), "initial_fontsize": 40}]
            fg_img = create_slide_content(content, (VIDEO_W, VIDEO_H), font_path, theme); fg_clip = ImageClip(np.array(fg_img)).set_duration(duration)
        
        if fg_clip: slide_clips.append(CompositeVideoClip([bg_clip, fg_clip]).set_start(current_time).set_duration(duration)); bg_idx += 1; current_time += duration
        else:
            if audio_clip: audio_clip.close()
    if not slide_clips: print("❌ ERROR: No slides were generated. Aborting video creation."); return
    total_dur = current_time; narration_audio = CompositeAudioClip(audio_clips_timeline)
    try:
        music_dir = os.path.join(utils.get_script_dir(), 'music'); music_files = [f for f in os.listdir(music_dir) if f.endswith('.mp3')] if os.path.exists(music_dir) else []
        if music_files:
            music_path = os.path.join(music_dir, random.choice(music_files)); music = AudioFileClip(music_path).audio_loop(duration=total_dur).volumex(0.25)
            final_audio = CompositeAudioClip([narration_audio, music]); print(f"  -> Using background music: {os.path.basename(music_path)}")
        else: final_audio = narration_audio; print("  -> No music files found. Skipping background music.")
    except Exception as e: print(f"      - Could not process music: {e}. Proceeding without music."); final_audio = narration_audio
    print("\n  -> Assembling video with transitions..."); final_video_clips = [clip.crossfadein(1.0) if i > 0 else clip for i, clip in enumerate(slide_clips)]
    video = CompositeVideoClip(final_video_clips, size=(VIDEO_W, VIDEO_H)).set_duration(total_dur)
    full_audio_path = os.path.join(utils.get_script_dir(), "outputs", "tmp", "vo_full.mp3")
    clips_for_concat = [clip for clip in audio_clips_timeline if isinstance(clip, AudioFileClip)]
    if clips_for_concat:
        full_narration_clip = concatenate_audioclips(clips_for_concat); full_narration_clip.write_audiofile(full_audio_path, codec='mp3', logger=None)
        subtitles_data = content_creator.generate_subtitles(full_audio_path); full_narration_clip.close()
    else: subtitles_data = None
    composited_elements = [video]
    if subtitles_data:
        def subtitle_generator(txt):
            wrapped_text = utils.wrap_text_for_subtitles(txt, max_chars_per_line=35)
            return TextClip(wrapped_text, font=font_path, fontsize=38, color='yellow', bg_color='rgba(0, 0, 0, 0.6)', align='center', method='caption')
        subtitle_clip = SubtitlesClip(subtitles_data, subtitle_generator).set_position(('center', 0.85), relative=True); composited_elements.append(subtitle_clip)
    footer_clip = TextClip("Sources: Multiple. Not financial advice.", font=font_path, fontsize=20, color='gray').set_position(('center', VIDEO_H * 0.95)); composited_elements.append(footer_clip)
    if assets.get('bg_credit'):
        credit_clip = TextClip(assets['bg_credit'], font=font_path, fontsize=16, color='gray').set_position((10, VIDEO_H - 30)); composited_elements.append(credit_clip)
    final_video = CompositeVideoClip(composited_elements, size=(VIDEO_W, VIDEO_H)).set_duration(total_dur); final_video.audio = final_audio
    print("  -> Writing final video file...")
    final_video.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", bitrate="3000k", threads=4, preset="medium", logger='bar')
    for clip in audio_clips_timeline:
        if clip:
            try: clip.close()
            except Exception: pass
