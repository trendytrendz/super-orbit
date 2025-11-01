# video_renderer.py
# v20.1.1

import os
import random
import numpy as np
from moviepy.editor import (ImageClip, AudioFileClip, CompositeVideoClip, CompositeAudioClip, concatenate_audioclips, concatenate_videoclips, TextClip, ColorClip, AudioClip)
from moviepy.video.tools.subtitles import SubtitlesClip

import config
import utils
import content_creator
import visual_elements

def make_video(slides, audio_paths, company, story_type, video_format, out_path, assets, theme, icon_svg, lang='en'):
    VIDEO_W, VIDEO_H = (config.VIDEO_W_LANDSCAPE, config.VIDEO_H_LANDSCAPE) if video_format == 'landscape' else (config.VIDEO_W_PORTRAIT, config.VIDEO_H_PORTRAIT)
    size = (VIDEO_W, VIDEO_H); font_path = theme['font']
    
    cta_layouts = [visual_elements.render_cta_slide_linear, visual_elements.render_cta_slide_circular, visual_elements.render_cta_slide_grid, visual_elements.render_cta_slide_diamond]
    bg_images = assets.get('bg_images', [])
    if specific_bg := assets.get('specific_bg_image'): bg_images.insert(0, specific_bg[0])

    blurred_bg_paths = {path: visual_elements.create_blurred_image(path, os.path.join(utils.get_script_dir(), "outputs", "tmp", f"bg_blurred_{i}.png")) for i, path in enumerate(bg_images)}
    
    audio_clips_timeline, slide_clips, current_time, bg_idx = [], [], 0.0, 0
    music, final_video, final_audio, subtitle_clip = None, None, None, None
    print("\n   -> Generating all slides and building timeline...")
    for slide_info in slides:
        key = slide_info['key']; audio_clip = None
        if key in audio_paths and os.path.exists(audio_paths[key]):
            try:
                audio_clip = AudioFileClip(audio_paths[key]); duration = max(audio_clip.duration + 1.8, 4.5); print(f"    - Audio found for slide '{key}'. Duration set to {duration:.2f}s.")
            except Exception as e: print(f"    - WARNING: Could not read audio for '{key}'. Skipping. Error: {e}"); continue
        else:
            duration = config.TITLE_SLIDE_DURATION; print(f"    - ⚠️ No audio for slide '{key}'. Using default duration {duration:.2f}s.")
            audio_clips_timeline.append(AudioClip(lambda t: [0, 0], duration=duration, fps=44100).set_start(current_time))
        
        if duration <= 0:
            if audio_clip: audio_clip.close(); continue
        if audio_clip: audio_clips_timeline.append(audio_clip.set_start(current_time))
        
        bg_path = bg_images[bg_idx % len(bg_images)] if bg_images else None
        final_bg_path = blurred_bg_paths.get(bg_path, bg_path) if slide_info.get('blur_bg', False) else bg_path
        base_bg_clip = visual_elements.create_pan_zoom_clip(duration, final_bg_path, size)
        
        composited_layers = [base_bg_clip]
        
        # FIX (Feedback #1): The render functions for single-layer slides now ONLY return the foreground.
        # The background is always handled here, ensuring it's never missing.
        fg_clip = None
        if slide_info['type'] == 'intro':
            fg_clip = visual_elements.render_intro_slide(slide_info, story_type, assets, theme, duration, size)
            animated_fg = visual_elements.apply_random_animation(fg_clip, 0, duration, size)
            composited_layers.append(animated_fg)
        elif slide_info['type'] == 'cta':
            selected_cta_renderer = random.choice(cta_layouts); print(f"    - Using CTA layout: {selected_cta_renderer.__name__}")
            fg_clip = selected_cta_renderer(slide_info, story_type, icon_svg, theme, duration, size)
            composited_layers.append(fg_clip)
        elif slide_info['type'] == 'news':
            composited_layers.extend(visual_elements.render_news_slide(slide_info, icon_svg, theme, duration, size))
        elif slide_info['type'] == 'summary':
            # This function returns a list with one item, so we extend
            composited_layers.extend(visual_elements.render_summary_slide(slide_info, theme, duration, size))
        elif slide_info['type'] == 'chart':
            composited_layers.extend(visual_elements.render_chart_slide(slide_info, size, duration))
        
        final_slide_clip = CompositeVideoClip(composited_layers, size=size).set_start(current_time).set_duration(duration)
        slide_clips.append(final_slide_clip); bg_idx += 1; current_time += duration

    if not slide_clips: print("❌ ERROR: No slides were generated. Aborting video creation."); return

    try:
        total_dur = current_time
        if audio_clips_timeline:
            narration_audio = CompositeAudioClip(audio_clips_timeline)
            music_dir = os.path.join(utils.get_script_dir(), 'music')
            if os.path.exists(music_dir) and (music_files := [f for f in os.listdir(music_dir) if f.endswith('.mp3')]):
                music_path = os.path.join(music_dir, random.choice(music_files))
                music = AudioFileClip(music_path).audio_loop(duration=total_dur).volumex(0.25); final_audio = CompositeAudioClip([narration_audio, music])
                print(f"  -> Using background music: {os.path.basename(music_path)}")
            else: final_audio = narration_audio; print("  -> No music files found. Skipping.")
        else: final_audio = None; music = None; print("⚠️ WARNING: No audio clips generated. Video will be silent.")
        
        print("\n  -> Assembling video with transitions..."); final_video_clips = [clip.crossfadein(0.5) if i > 0 else clip for i, clip in enumerate(slide_clips)]
        video = CompositeVideoClip(final_video_clips, size=size).set_duration(total_dur)
        
        full_audio_path = os.path.join(utils.get_script_dir(), "outputs", "tmp", "vo_full.mp3")
        if clips_for_concat := [c for c in audio_clips_timeline if isinstance(c, AudioFileClip)]:
            concatenate_audioclips(clips_for_concat).write_audiofile(full_audio_path, codec='mp3', logger=None)
            subtitles_data = content_creator.generate_subtitles(full_audio_path)
        else: subtitles_data = None
        
        composited_elements = [video]
        if subtitles_data:
            def subtitle_generator(txt):
                return TextClip(utils.wrap_text_for_subtitles(txt, max_chars_per_line=35), font=font_path, fontsize=38, color='yellow', bg_color='rgba(0, 0, 0, 0.6)', align='center', method='caption')
            composited_elements.append(SubtitlesClip(subtitles_data, subtitle_generator).set_position(('center', 0.85), relative=True))
        
        composited_elements.append(TextClip("Sources: Multiple. Not financial advice.", font=font_path, fontsize=20, color='gray').set_position(('center', VIDEO_H * 0.95)))
        if assets.get('bg_credit'): composited_elements.append(TextClip(assets['bg_credit'], font=font_path, fontsize=16, color='gray').set_position((10, VIDEO_H - 30)))
        
        final_video = CompositeVideoClip(composited_elements, size=size).set_duration(total_dur); final_video.audio = final_audio
        
        print("  -> Writing final video file..."); final_video.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", bitrate="3000k", threads=4, logger='bar')
    
    finally:
        print("  -> Cleaning up video and audio resources...")
        clips_to_close = [final_video, music, subtitle_clip] + audio_clips_timeline
        for clip in clips_to_close:
            if clip:
                try: clip.close()
                except Exception: pass
