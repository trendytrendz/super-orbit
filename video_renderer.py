import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import cairosvg
import io
from moviepy.editor import (ImageClip, AudioFileClip, CompositeVideoClip, CompositeAudioClip, concatenate_audioclips, concatenate_videoclips, TextClip, ColorClip, AudioClip)
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
    fg_img = Image.new("RGBA", size, (0,0,0,0))
    with Image.open(chart_path) as chart_img_file:
        chart_img = chart_img_file.convert("RGBA")
        chart_img.thumbnail((int(size[0] * 0.95), int(size[1] * 0.95)), Image.Resampling.LANCZOS)
        paste_x = (size[0] - chart_img.width) // 2
        paste_y = (size[1] - chart_img.height) // 2
        fg_img.paste(chart_img, (paste_x, paste_y), chart_img)
    return fg_img

def create_slide_content(content_elements, size, font_path, theme):
    fg_img = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(fg_img)
    for element in content_elements:
        if element['type'] == 'text':
            font = utils.get_optimal_font_size(element['text'], element.get('initial_fontsize', 70), element.get('box', size)[0], element.get('box', size)[1], font_path)
            lines = utils.wrap_text_pil(element['text'], font, element.get('box', size)[0])
            line_heights = [draw.textbbox((0,0), line, font=font)[3] for line in lines]
            total_text_height = sum(line_heights) + (len(lines) - 1) * (font.size * 0.2)
            y_pos = element['position'][1] - total_text_height / 2
            for i, line in enumerate(lines):
                line_width = draw.textlength(line, font=font)
                x_pos = element['position'][0] - line_width / 2
                draw.text((x_pos + 3, y_pos + 3), line, font=font, fill="#00000088")
                draw.text((x_pos, y_pos), line, font=font, fill=element.get('color', theme['text']))
                y_pos += line_heights[i] * 1.2
        elif element['type'] == 'image':
            img_to_paste_file = None
            if 'data' in element and isinstance(element['data'], Image.Image):
                img_to_paste_file = element['data']
            elif 'path' in element:
                 with Image.open(element['path']) as opened_img:
                    img_to_paste_file = opened_img.convert("RGBA")
            if img_to_paste_file:
                img_to_paste = img_to_paste_file.copy()
                img_to_paste.thumbnail(element.get('size', (100, 100)), Image.Resampling.LANCZOS)
                paste_pos = (int(element['position'][0] - img_to_paste.width / 2), int(element['position'][1] - img_to_paste.height / 2))
                fg_img.paste(img_to_paste, paste_pos, img_to_paste)
    return fg_img

def create_typing_text_clip(text, duration, font, initial_fontsize, box_size, pos, color):
    font_obj = utils.get_optimal_font_size(text, initial_fontsize, box_size[0], box_size[1], font)
    wrapped_lines = utils.wrap_text_pil(text, font_obj, box_size[0])
    full_text_for_anim = "\n".join(wrapped_lines)
    clips = []
    text_len = len(full_text_for_anim)
    char_duration = duration / (text_len + 1) if text_len > 0 else duration
    for i in range(1, text_len + 1):
        sub_text = full_text_for_anim[:i]
        txt_clip = TextClip(sub_text, font=font, fontsize=font_obj.size, color=color, align='center', size=box_size, method='caption').set_duration(char_duration)
        clips.append(txt_clip)
    if not clips:
        return ColorClip(size=box_size, color=(0,0,0,0), duration=duration).set_position(pos), None
    animation = concatenate_videoclips(clips)
    final_frame = TextClip(full_text_for_anim, font=font, fontsize=font_obj.size, color=color, align='center', size=box_size, method='caption')
    return animation.set_position(pos), final_frame.set_position(pos)

def create_pan_zoom_clip(duration, bg_path, size):
    bg_color_tuple = tuple(int(config.BG_COLOR.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    if not bg_path:
        return ColorClip(size=size, color=bg_color_tuple, duration=duration)
    try:
        zoom_margin = 1.2
        img = Image.open(bg_path)
        target_aspect = size[0] / size[1]
        img_aspect = img.width / img.height
        if img_aspect > target_aspect:
            new_width = int(target_aspect * img.height)
            offset = (img.width - new_width) / 2
            img = img.crop((offset, 0, img.width - offset, img.height))
        else:
            new_height = int(img.width / target_aspect)
            offset = (img.height - new_height) / 2
            img = img.crop((0, offset, img.width, img.height - offset))
        resized_w, resized_h = int(size[0] * zoom_margin), int(size[1] * zoom_margin)
        x_start, y_start = 0, 0
        x_end, y_end = size[0] - resized_w, size[1] - resized_h
        pan_path = random.choice([((x_start, y_start), (x_end, y_end)), ((x_end, y_start), (x_start, y_end)), ((x_start, y_end), (x_end, y_start)), ((x_end, y_end), (x_start, y_start))])
        return ImageClip(np.array(img)).set_duration(duration).resize((resized_w, resized_h)).set_position(lambda t: (pan_path[0][0] + (pan_path[1][0] - pan_path[0][0]) * t / duration, pan_path[0][1] + (pan_path[1][1] - pan_path[0][1]) * t / duration))
    except Exception as e:
        print(f"  - Warning: Could not create pan/zoom BG, using static color. Error: {e}")
        return ColorClip(size=size, color=bg_color_tuple, duration=duration)

def make_video(slides, audio_paths, company, nse_symbol, video_format, out_path, assets, theme, icon_svg, lang='en'):
    VIDEO_W, VIDEO_H = (config.VIDEO_W_LANDSCAPE, config.VIDEO_H_LANDSCAPE) if video_format == 'landscape' else (config.VIDEO_W_PORTRAIT, config.VIDEO_H_PORTRAIT)
    font_path = theme['font']
    bg_images = assets.get('bg_images', [])
    blurred_bg_paths = {}
    
    for i, img_path in enumerate(bg_images):
        output_path = os.path.join(utils.get_script_dir(), "outputs", "tmp", f"bg_blurred_{i}.jpg")
        if blurred_path := create_blurred_image(img_path, output_path):
            blurred_bg_paths[img_path] = blurred_path

    audio_clips_timeline, slide_clips, current_time, bg_idx = [], [], 0.0, 0
    music, final_video, final_audio, subtitle_clip = None, None, None, None
    
    print("   -> Generating all slides and building timeline...")
    for slide_info in slides:
        key, audio_clip, duration = slide_info['key'], None, 0
        if key in audio_paths and os.path.exists(audio_paths[key]):
            try:
                audio_clip = AudioFileClip(audio_paths[key])
                audio_duration = audio_clip.duration
                padding = 1.8
                duration = audio_duration + padding
                duration = max(duration, 4.5)
            except Exception as e:
                print(f"    - WARNING: Could not read audio duration for '{key}'. Skipping. Error: {e}")
                continue
        else:
            duration = config.TITLE_SLIDE_DURATION
            silent_audio = AudioClip(lambda t: [0, 0], duration=duration, fps=44100)
            audio_clips_timeline.append(silent_audio.set_start(current_time))
        
        if duration <= 0:
            if audio_clip: audio_clip.close()
            continue
        
        if audio_clip:
            audio_clips_timeline.append(audio_clip.set_start(current_time))

        bg_path = bg_images[bg_idx % len(bg_images)] if bg_images else None
        final_bg_path = blurred_bg_paths.get(bg_path, bg_path) if slide_info.get('blur_bg', False) else bg_path
        bg_clip = create_pan_zoom_clip(duration, final_bg_path, (VIDEO_W, VIDEO_H))
        fg_clip = None

        if slide_info['type'] == 'intro':
            content = [{"type": "text", "text": slide_info['text'], "position": (VIDEO_W / 2, VIDEO_H * 0.65), "box": (VIDEO_W * 0.8, VIDEO_H * 0.4), "initial_fontsize": 90}]
            
            # --- NEW DYNAMIC LOGO LAYOUT ENGINE ---
            if logos_pil := [logo for logo in slide_info.get('logos', []) if logo]:
                num_logos = len(logos_pil)
                max_total_width = VIDEO_W * 0.8
                max_logo_height = VIDEO_H * 0.25
                
                scaled_widths = []
                for logo in logos_pil:
                    aspect_ratio = logo.width / logo.height
                    scaled_widths.append(max_logo_height * aspect_ratio)
                
                total_scaled_width = sum(scaled_widths)
                scale_factor = 1.0
                if total_scaled_width > max_total_width:
                    scale_factor = max_total_width / total_scaled_width

                logo_spacing = 30 * scale_factor
                total_final_width = sum(w * scale_factor for w in scaled_widths) + logo_spacing * (num_logos - 1)
                start_x = (VIDEO_W - total_final_width) / 2
                
                current_x = start_x
                for i, logo in enumerate(logos_pil):
                    final_h = int(max_logo_height * scale_factor)
                    final_w = int(scaled_widths[i] * scale_factor)
                    logo_center_x = current_x + final_w / 2
                    content.insert(0, {"type": "image", "data": logo, "size": (final_w, final_h), "position": (logo_center_x, VIDEO_H * 0.3)})
                    current_x += final_w + logo_spacing
            
            elif slide_info.get('logo') and assets.get('logo'):
                logo = assets.get('logo')
                max_w, max_h = int(VIDEO_W * 0.5), int(VIDEO_H * 0.25)
                logo.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
                content.insert(0, {"type": "image", "data": logo, "size": logo.size, "position": (VIDEO_W/2, VIDEO_H * 0.3)})
            
            fg_img = create_slide_content(content, (VIDEO_W, VIDEO_H), font_path, theme)
            fg_clip = ImageClip(np.array(fg_img)).set_duration(duration)
        
        elif slide_info['type'] == 'news':
            png_buffer = io.BytesIO(); cairosvg.svg2png(bytestring=icon_svg[slide_info['icon']], write_to=png_buffer, output_height=60); png_buffer.seek(0)
            icon_array = np.array(Image.open(png_buffer)); icon_clip = ImageClip(icon_array).set_duration(duration).set_position((VIDEO_W * 0.1, VIDEO_H * 0.15))
            typing_duration = min(3.5, duration * 0.7); animation, final_text = create_typing_text_clip(slide_info['text'], typing_duration, font_path, 108, (VIDEO_W * 0.85, VIDEO_H * 0.8), ('center', 'center'), theme['accent']); hold_duration = duration - animation.duration
            if hold_duration > 0 and final_text: hold_clip = final_text.set_duration(hold_duration); text_element = concatenate_videoclips([animation, hold_clip])
            else: text_element = animation.set_duration(duration)
            fg_clip = CompositeVideoClip([text_element, icon_clip])
        
        elif slide_info['type'] == 'summary':
            is_title_slide = slide_info.get('is_title', False); font_size = 90 if is_title_slide else 60; content = [{"type": "text", "text": slide_info['text'], "position": (VIDEO_W / 2, VIDEO_H / 2), "box": (VIDEO_W * 0.85, VIDEO_H * 0.8), "initial_fontsize": font_size}]; fg_img = create_slide_content(content, (VIDEO_W, VIDEO_H), font_path, theme); fg_clip = ImageClip(np.array(fg_img)).set_duration(duration)
        
        elif slide_info['type'] == 'chart':
            if (path := slide_info.get('path')) and os.path.exists(path):
                fg_img = create_chart_slide_image(path, (VIDEO_W, VIDEO_H)); fg_clip = ImageClip(np.array(fg_img)).set_duration(duration)
            else: print(f"    - WARNING: Chart path for slide '{key}' not found. Skipping visuals."); fg_clip = ColorClip(size=(1,1), color=(0,0,0,0), duration=duration)
        
        elif slide_info['type'] == 'cta':
            icon_data = {}
            for name in ['like', 'comment', 'share']: png_buffer = io.BytesIO(); cairosvg.svg2png(bytestring=icon_svg[name], write_to=png_buffer, output_height=80); png_buffer.seek(0); icon_data[name] = Image.open(png_buffer)
            icon_size = (80, 80); y_pos_icon = VIDEO_H * 0.45; y_pos_text = y_pos_icon + 80; content = [{"type": "image", "data": icon_data['like'], "size": icon_size, "position": (VIDEO_W * 0.25, y_pos_icon)}, {"type": "text", "text": "Like", "position": (VIDEO_W * 0.25, y_pos_text), "initial_fontsize": 40}, {"type": "image", "data": icon_data['comment'], "size": icon_size, "position": (VIDEO_W * 0.5, y_pos_icon)}, {"type": "text", "text": "Comment", "position": (VIDEO_W * 0.5, y_pos_text), "initial_fontsize": 40}, {"type": "image", "data": icon_data['share'], "size": icon_size, "position": (VIDEO_W * 0.75, y_pos_icon)}, {"type": "text", "text": "Share", "position": (VIDEO_W * 0.75, y_pos_text), "initial_fontsize": 40}]; fg_img = create_slide_content(content, (VIDEO_W, VIDEO_H), font_path, theme); fg_clip = ImageClip(np.array(fg_img)).set_duration(duration)
        
        if fg_clip: slide_clips.append(CompositeVideoClip([bg_clip, fg_clip]).set_start(current_time).set_duration(duration)); bg_idx += 1; current_time += duration
        else:
            if audio_clip: audio_clip.close()

    if not slide_clips: print("❌ ERROR: No slides were generated. Aborting video creation."); return
    
    try:
        total_dur = current_time
        if audio_clips_timeline:
            narration_audio = CompositeAudioClip(audio_clips_timeline); music_dir = os.path.join(utils.get_script_dir(), 'music'); music_files = [f for f in os.listdir(music_dir) if f.endswith('.mp3')] if os.path.exists(music_dir) else []
            if music_files: music_path = os.path.join(music_dir, random.choice(music_files)); music = AudioFileClip(music_path).audio_loop(duration=total_dur).volumex(0.25); final_audio = CompositeAudioClip([narration_audio, music]); print(f"  -> Using background music: {os.path.basename(music_path)}")
            else: final_audio = narration_audio; print("  -> No music files found. Skipping background music.")
        else: print("⚠️ WARNING: No audio clips were generated. The final video will be silent."); final_audio = None; music = None
        print("\n  -> Assembling video with transitions..."); final_video_clips = [clip.crossfadein(1.0) if i > 0 else clip for i, clip in enumerate(slide_clips)]; video = CompositeVideoClip(final_video_clips, size=(VIDEO_W, VIDEO_H)).set_duration(total_dur)
        full_audio_path = os.path.join(utils.get_script_dir(), "outputs", "tmp", "vo_full.mp3")
        clips_for_concat = [clip for clip in audio_clips_timeline if isinstance(clip, AudioFileClip)]
        if clips_for_concat:
            full_narration_clip = concatenate_audioclips(clips_for_concat); full_narration_clip.write_audiofile(full_audio_path, codec='mp3', logger=None)
            subtitles_data = content_creator.generate_subtitles(full_audio_path)
            full_narration_clip.close()
        else: subtitles_data = None
        composited_elements = [video]
        if subtitles_data:
            def subtitle_generator(txt):
                wrapped_text = utils.wrap_text_for_subtitles(txt, max_chars_per_line=35); return TextClip(wrapped_text, font=font_path, fontsize=38, color='yellow', bg_color='rgba(0, 0, 0, 0.6)', align='center', method='caption')
            subtitle_clip = SubtitlesClip(subtitles_data, subtitle_generator).set_position(('center', 0.85), relative=True); composited_elements.append(subtitle_clip)
        footer_clip = TextClip("Sources: Multiple. Not financial advice.", font=font_path, fontsize=20, color='gray').set_position(('center', VIDEO_H * 0.95)); composited_elements.append(footer_clip)
        if assets.get('bg_credit'): credit_clip = TextClip(assets['bg_credit'], font=font_path, fontsize=16, color='gray').set_position((10, VIDEO_H - 30)); composited_elements.append(credit_clip)
        final_video = CompositeVideoClip(composited_elements, size=(VIDEO_W, VIDEO_H)).set_duration(total_dur); final_video.audio = final_audio
        print("  -> Writing final video file..."); final_video.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", bitrate="3000k", threads=4, logger='bar')
    finally:
        print("  -> Cleaning up video and audio resources...")
        narration_audio_to_close = [CompositeAudioClip(audio_clips_timeline)] if audio_clips_timeline else []
        clips_to_close = [final_video, music, subtitle_clip] + narration_audio_to_close
        for clip in clips_to_close:
            if clip:
                try: clip.close()
                except Exception: pass
