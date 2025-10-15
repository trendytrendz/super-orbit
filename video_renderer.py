# video_renderer.py
import os
import random
import numpy as np
from PIL import Image, ImageDraw
import cairosvg

from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip, CompositeAudioClip,
    concatenate_audioclips, concatenate_videoclips, TextClip, ColorClip
)
from moviepy.video.tools.subtitles import SubtitlesClip

import config
import utils
import content_creator

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
            font = utils.get_optimal_font_size(element['text'], element.get('initial_fontsize', 70), 
                                         element.get('box', size)[0], element.get('box', size)[1], font_path)
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
             with Image.open(element['path']) as img_to_paste_file:
                img_to_paste = img_to_paste_file.convert("RGBA")
                img_to_paste.thumbnail(element['size'], Image.Resampling.LANCZOS)
                paste_pos = (int(element['position'][0] - img_to_paste.width / 2), int(element['position'][1] - img_to_paste.height / 2))
                fg_img.paste(img_to_paste, paste_pos, img_to_paste)
    return fg_img

def create_typing_text_clip(text, duration, font, initial_fontsize, box_size, pos, color):
    font_obj = utils.get_optimal_font_size(text, initial_fontsize, box_size[0], box_size[1], font)
    wrapped_lines = utils.wrap_text_pil(text, font_obj, box_size[0])
    full_text_for_anim = "\n".join(wrapped_lines)
    clips = []; text_len = len(full_text_for_anim); char_duration = duration / (text_len + 1) if text_len > 0 else duration
    for i in range(text_len):
        sub_text = full_text_for_anim[:i+1]
        txt_clip = TextClip(sub_text, font=font, fontsize=font_obj.size, color=color, align='center', size=box_size, method='caption').set_duration(char_duration)
        clips.append(txt_clip)
    if not clips: return ColorClip(size=(1,1), color=(0,0,0,0), duration=duration)
    return concatenate_videoclips(clips).set_position(pos)

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

def make_video(slides, audio_paths, company, nse_symbol, video_format, out_path, assets, theme, icon_svg):
    VIDEO_W, VIDEO_H = (config.VIDEO_W_LANDSCAPE, config.VIDEO_H_LANDSCAPE) if video_format == 'landscape' else (config.VIDEO_W_PORTRAIT, config.VIDEO_H_PORTRAIT)
    font_path = theme['font']; bg_images = assets.get('bg_images', [])
    audio_clips_timeline = []; slide_clips = []; current_time = 0.0; bg_idx = 0
    print("   -> Generating all slides and building timeline...")

    for slide_info in slides:
        key = slide_info['key']
        if key not in audio_paths or not os.path.exists(audio_paths[key]): print(f"    - Skipping slide '{key}' because audio is missing."); continue
        try: duration = AudioFileClip(audio_paths[key]).duration + 1.0
        except Exception as e: print(f"    - WARNING: Could not read audio duration for '{key}'. Skipping slide. Error: {e}"); continue
        audio_clips_timeline.append(AudioFileClip(audio_paths[key]).set_start(current_time))
        bg_clip = create_pan_zoom_clip(duration, bg_images[bg_idx % len(bg_images)] if bg_images else None, (VIDEO_W, VIDEO_H)); fg_clip = None
        
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
            text_clip = create_typing_text_clip(slide_info['text'], duration, font_path, 108, (VIDEO_W * 0.85, VIDEO_H * 0.8), ('center', 'center'), theme['accent']); fg_clip = CompositeVideoClip([text_clip, icon_clip])
        elif slide_info['type'] == 'summary':
            content = [{"type": "text", "text": slide_info['text'], "position": (VIDEO_W / 2, VIDEO_H / 2), "box": (VIDEO_W * 0.85, VIDEO_H * 0.8), "initial_fontsize": 60}]
            fg_img = create_slide_content(content, (VIDEO_W, VIDEO_H), font_path, theme); fg_clip = ImageClip(np.array(fg_img)).set_duration(duration)
        elif slide_info['type'] == 'chart':
            if slide_info.get('path') and os.path.exists(slide_info['path']):
                fg_img = create_chart_slide_image(slide_info['path'], (VIDEO_W, VIDEO_H)); fg_clip = ImageClip(np.array(fg_img)).set_duration(duration)
            else: print(f"    - WARNING: Chart path for slide '{key}' not found. Skipping slide visuals."); fg_clip = ColorClip(size=(1,1), color=(0,0,0,0), duration=duration)
        elif slide_info['type'] == 'cta':
            icon_paths = {}; [cairosvg.svg2png(bytestring=svg, write_to=os.path.join(utils.get_script_dir(), "outputs", "tmp", f"icon_{name}.png"), output_height=80) for name, svg in config.OUTRO_ICONS.items()]; [icon_paths.update({name: os.path.join(utils.get_script_dir(), "outputs", "tmp", f"icon_{name}.png")}) for name in config.OUTRO_ICONS.keys()]
            icon_size = (80, 80); y_pos_icon = VIDEO_H * 0.45; y_pos_text = y_pos_icon + 80
            content = [{"type": "image", "path": icon_paths['like'], "size": icon_size, "position": (VIDEO_W * 0.25, y_pos_icon)}, {"type": "text", "text": "Like", "position": (VIDEO_W * 0.25, y_pos_text), "initial_fontsize": 40}, {"type": "image", "path": icon_paths['comment'], "size": icon_size, "position": (VIDEO_W * 0.5, y_pos_icon)}, {"type": "text", "text": "Comment", "position": (VIDEO_W * 0.5, y_pos_text), "initial_fontsize": 40}, {"type": "image", "path": icon_paths['share'], "size": icon_size, "position": (VIDEO_W * 0.75, y_pos_icon)}, {"type": "text", "text": "Share", "position": (VIDEO_W * 0.75, y_pos_text), "initial_fontsize": 40}]
            fg_img = create_slide_content(content, (VIDEO_W, VIDEO_H), font_path, theme); fg_clip = ImageClip(np.array(fg_img)).set_duration(duration)
        
        if fg_clip:
            slide_clips.append(CompositeVideoClip([bg_clip, fg_clip]).set_start(current_time).set_duration(duration)); bg_idx += 1; current_time += duration
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
    clips_for_concat = [AudioFileClip(path) for key, path in audio_paths.items() if key in [s['key'] for s in slides] and os.path.exists(path)]
    if clips_for_concat:
        full_narration_clip = concatenate_audioclips(clips_for_concat); full_narration_clip.write_audiofile(full_audio_path, codec='mp3', logger=None)
        subtitles_data = content_creator.generate_subtitles(full_audio_path); full_narration_clip.close()
    else: subtitles_data = None
    composited_elements = [video]
    if subtitles_data:
        def subtitle_generator(txt): return TextClip(txt, font=font_path, fontsize=38, color='white', stroke_color='#000000CC', stroke_width=2.5, align='center', method='caption')
        subtitle_clip = SubtitlesClip(subtitles_data, subtitle_generator).set_position(('center', 0.88), relative=True); composited_elements.append(subtitle_clip)
    footer_clip = TextClip("Sources: Multiple. Not financial advice.", font=font_path, fontsize=20, color='gray').set_position(('center', VIDEO_H * 0.95)); composited_elements.append(footer_clip)
    if assets.get('bg_credit'):
        credit_clip = TextClip(assets['bg_credit'], font=font_path, fontsize=16, color='gray').set_position((10, VIDEO_H - 30)); composited_elements.append(credit_clip)
    final_video = CompositeVideoClip(composited_elements, size=(VIDEO_W, VIDEO_H)).set_duration(total_dur); final_video.audio = final_audio
    print("  -> Writing final video file...")
    final_video.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", bitrate="3000k", threads=4, preset="medium", logger='bar')
    for clip in audio_clips_timeline + clips_for_concat:
        if clip:
            try: clip.close()
            except Exception: pass
