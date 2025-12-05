# video_renderer.py
# v24.2.16 - Fixed Audio Attachment & Validation

import os
import random
import numpy as np
from PIL import Image, ImageDraw
from moviepy.editor import (
    AudioFileClip, CompositeVideoClip, CompositeAudioClip, 
    concatenate_videoclips, ImageClip
)
from . import config
from . import utils
from . import visual_elements

def _create_subtitle_clip_pil(text, duration, size):
    """Creates subtitles using PIL (bypasses ImageMagick)."""
    if not text: return None
    W, H = size
    
    img = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    font_size = 32 if W < H else 40
    font = visual_elements.load_font(config.DEFAULT_FONT, font_size)
    
    clean_text = text.replace('\n', ' ').strip()
    if len(clean_text) > 160: clean_text = clean_text[:157] + "..."
    lines = utils.wrap_text_pil(clean_text, font, W * 0.9)
    
    if not lines: return None
    
    line_h = font_size * 1.3
    total_h = len(lines) * line_h + 20
    
    box_y = H * 0.85 - 10
    draw.rectangle([0, box_y, W, box_y + total_h], fill=(0,0,0, 160))
    
    text_y = box_y + 10
    for line in lines:
        for off in [(-1,-1), (-1,1), (1,-1), (1,1)]:
            draw.text((W/2 + off[0], text_y + off[1]), line, font=font, fill="black", anchor="mt")
        draw.text((W/2, text_y), line, font=font, fill="yellow", anchor="mt")
        text_y += line_h
        
    return ImageClip(np.array(img)).set_duration(duration)

def make_video(slides, audio_paths, company, story_type, video_format, out_path, assets, theme, icon_svg, lang='en'):
    print(f"\n🎥 STARTING VIDEO RENDER: {story_type} for {company}")
    
    VIDEO_W, VIDEO_H = (config.VIDEO_W_LANDSCAPE, config.VIDEO_H_LANDSCAPE) if video_format == 'landscape' else (config.VIDEO_W_PORTRAIT, config.VIDEO_H_PORTRAIT)
    size = (VIDEO_W, VIDEO_H)
    
    # 1. Resources
    cta_layouts = [
        visual_elements.render_cta_slide_linear, 
        visual_elements.render_cta_slide_circular, 
        visual_elements.render_cta_slide_grid,
        visual_elements.render_cta_slide_diamond
    ]
    
    bg_images = assets.get('bg_images', [])
    if not bg_images: bg_images = _create_fallback_backgrounds(5, size)
    
    blurred_bg_paths = {}
    for path in bg_images:
        if os.path.exists(path):
            b_path = os.path.join(config.TMP_IMG_DIR, f"blur_{os.path.basename(path)}")
            if not os.path.exists(b_path): blurred_bg_paths[path] = visual_elements.create_blurred_image(path, b_path)
            else: blurred_bg_paths[path] = b_path

    final_clips = []
    bg_idx = 0
    
    print("\n   -> Validating Audio Paths:")
    validated_audio_paths = {}
    for slide in slides:
        k = slide['key']
        if k in audio_paths:
            p = audio_paths[k]
            if not os.path.isabs(p): p = os.path.abspath(p)
            
            # FIX: Lowered threshold to 100 bytes (was 1000)
            if os.path.exists(p) and os.path.getsize(p) > 100:
                validated_audio_paths[k] = p
                print(f"      ✅ {k}: {os.path.basename(p)} ({os.path.getsize(p)} bytes)")
            else:
                print(f"      ❌ {k}: File missing or too small (<100b) at {p}")

    # 2. Build Slides
    for i, slide_info in enumerate(slides):
        key = slide_info['key']
        print(f"    - Processing Slide {i+1}: '{key}'")
        
        # AUDIO LOADING
        audio_clip = None
        duration = config.TITLE_SLIDE_DURATION
        
        if key in validated_audio_paths:
            try:
                # Load audio and force compatibility check
                audio_clip = AudioFileClip(validated_audio_paths[key])
                duration = audio_clip.duration + 0.5 # Add buffer
                print(f"      🔉 Audio loaded: {duration:.2f}s")
            except Exception as e:
                print(f"      ⚠️  Audio Load Error for '{key}': {e}")
                audio_clip = None
        else:
            print(f"      ⚠️  No audio found for '{key}', using default duration.")
        
        # VISUAL
        bg_path = bg_images[bg_idx % len(bg_images)]
        final_bg = blurred_bg_paths.get(bg_path, bg_path) if slide_info.get('blur_bg') else bg_path
        layers = [visual_elements.create_pan_zoom_clip(duration, final_bg, size)]
        
        try:
            fg = None
            st = slide_info['type']
            if st == 'intro':
                fg = visual_elements.render_intro_slide(slide_info, story_type, assets, theme, duration, size)
                fg = visual_elements.apply_random_animation(fg, 0, duration, size)
            elif st == 'sector': fg = visual_elements.render_sector_slide(slide_info, theme, duration, size)
            elif st == 'management': fg = visual_elements.render_management_slide(slide_info, theme, duration, size)
            elif st == 'cta': 
                fg = random.choice(cta_layouts)(slide_info, story_type, icon_svg, theme, duration, size)
            elif st == 'chart': layers.extend(visual_elements.render_chart_slide(slide_info, size, duration))
            elif st == 'news': layers.extend(visual_elements.render_news_slide(slide_info, icon_svg, theme, duration, size))
            elif st == 'summary': layers.extend(visual_elements.render_summary_slide(slide_info, theme, duration, size))
            
            if fg: layers.append(fg)
        except Exception as e: print(f"      ❌ Visual Render error: {e}")

        # SUBTITLES
        txt = slide_info.get('script_text', '') or (slide_info['text'] if len(slide_info.get('text','')) > 50 else "")
        if txt:
            sub = _create_subtitle_clip_pil(txt, duration, size)
            if sub: layers.append(sub)

        # COMPOSITE
        # FIX: Explicitly set audio on the composite clip
        clip = CompositeVideoClip(layers, size=size).set_duration(duration)
        if audio_clip:
            clip = clip.set_audio(audio_clip)
        
        final_clips.append(clip)
        bg_idx += 1

    # 3. Assembly
    try:
        print(f"   -> Stitching {len(final_clips)} clips...")
        final_video = concatenate_videoclips(final_clips, method="compose")
        
        # Music Mixing
        music_file = None
        dirs = [config.MUSIC_DIR, os.path.join(os.getcwd(), "music")]
        for d in dirs:
            if os.path.exists(d):
                fs = [f for f in os.listdir(d) if f.endswith('mp3') or f.endswith('wav')]
                if fs: 
                    music_file = os.path.join(d, random.choice(fs))
                    break
        
        if music_file and final_video.audio:
            print(f"      🎵 Mixing Background Music: {os.path.basename(music_file)}")
            try:
                music = AudioFileClip(music_file)
                # Loop music and lower volume
                if music.duration < final_video.duration:
                    music = music.audio_loop(duration=final_video.duration)
                else:
                    music = music.subclip(0, final_video.duration)
                
                music = music.volumex(0.10) # 10% Volume
                
                # Mix voice and music
                final_audio = CompositeAudioClip([final_video.audio, music])
                final_video = final_video.set_audio(final_audio)
            except Exception as e:
                print(f"      ⚠️ Music Mix Failed: {e}")

        print(f"   -> Rendering to {out_path}...")
        final_video.write_videofile(
            out_path, 
            fps=24, 
            codec='libx264', 
            audio_codec='aac', # Ensure standard audio codec
            bitrate='5000k', 
            threads=4, 
            logger='bar'
        )
        
    except Exception as e:
        print(f"❌ Assembly error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup to release file locks
        for c in final_clips: 
            try: 
                if c.audio: c.audio.close()
                c.close() 
            except: pass

def _create_fallback_backgrounds(num, size):
    try:
        backgrounds = []
        os.makedirs(config.TMP_IMG_DIR, exist_ok=True)
        colors = [(30, 40, 60), (40, 30, 50), (35, 45, 35), (50, 35, 30), (35, 35, 45)]
        for i in range(num):
            bg_path = os.path.join(config.TMP_IMG_DIR, f"color_bg_{i}.jpg")
            img = Image.new('RGB', size, colors[i % len(colors)])
            draw = ImageDraw.Draw(img)
            for y in range(size[1]):
                r = int(colors[i % len(colors)][0] + (y/size[1])*10)
                g = int(colors[i % len(colors)][1] + (y/size[1])*8)
                b = int(colors[i % len(colors)][2] + (y/size[1])*12)
                draw.line([(0, y), (size[0], y)], fill=(r, g, b))
            img.save(bg_path)
            backgrounds.append(bg_path)
        return backgrounds
    except Exception:
        return []