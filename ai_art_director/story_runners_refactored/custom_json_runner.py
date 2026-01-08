import json
import os
import random
import requests
import wave
import struct
import shutil
import subprocess
import numpy as np
from PIL import Image, ImageDraw 
from moviepy.editor import (
    concatenate_videoclips, AudioFileClip, CompositeAudioClip, 
    CompositeVideoClip, AudioClip, ColorClip, VideoFileClip,
    ImageClip, concatenate_audioclips
)
from ai_art_director.visuals import compositor, effects, core
from ai_art_director.audio_generator import audio_generator
from ai_art_director.config import TMP_DIR, OUTPUT_DIR, MUSIC_DIR, CUSTOM_INPUT_DIR, ASSETS_DIR, SFX_DIR
from ai_art_director import utils
from ai_art_director.visuals.theme_config import THEMES

VALID_RANDOM_THEMES = [
    "breaking_bar", "market_dashboard", "glass_stack", 
    "neo_brutalist", "vertical_ticker", "split_deck", "kinetic_typo"
]

class CustomJsonStory:
    def __init__(self, config_dict=None):
        self.config = config_dict or {}
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(TMP_DIR, exist_ok=True)
        os.makedirs(SFX_DIR, exist_ok=True)
        
        self.wav_dir = os.path.join(TMP_DIR, "sanitized_audio")
        os.makedirs(self.wav_dir, exist_ok=True)
        
        self.ensure_sfx_assets()

    def make_silent_wave(self, filename, duration=1.0):
        try:
            with wave.open(filename, 'w') as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(44100)
                n_frames = int(44100 * duration); data = struct.pack('<h', 0) * n_frames; wf.writeframes(data)
            return True
        except: return False

    def ensure_sfx_assets(self):
        # Don't download if ANY sound exists
        existing = [f for f in os.listdir(SFX_DIR) if f.lower().endswith(('.wav', '.mp3', '.flac', '.aiff'))]
        if existing:
            print(f"   ✅ Found {len(existing)} SFX files in {SFX_DIR}", flush=True)
            return

        print("   🛠️  No SFX found. Attempting download...", flush=True)
        swoosh_path = os.path.join(SFX_DIR, "swoosh.mp3")
        try:
            r = requests.get("https://freesound.org/data/previews/614/614603_11086036-lq.mp3", timeout=10)
            if r.status_code == 200:
                with open(swoosh_path, 'wb') as f: f.write(r.content)
        except:
            self.make_silent_wave(os.path.join(SFX_DIR, "swoosh.wav"), duration=1.0)

    def sanitize_audio(self, path):
        if not path or not os.path.exists(path): return None
        base_name = os.path.splitext(os.path.basename(path))[0]
        safe_wav = os.path.join(self.wav_dir, f"{base_name}_{random.randint(1000,9999)}.wav")
        try:
            # FIX: Only use -acodec pcm_s16le
            cmd = ['ffmpeg', '-i', path, '-ar', '44100', '-ac', '2', '-acodec', 'pcm_s16le', '-y', '-v', 'error', safe_wav]
            subprocess.run(cmd, check=True)
            if os.path.exists(safe_wav): return AudioFileClip(safe_wav)
        except:
            try:
                clip = AudioFileClip(path)
                clip.write_audiofile(safe_wav, fps=44100, logger=None)
                return AudioFileClip(safe_wav)
            except: pass
        return None

    def get_random_sfx(self):
        """Pick a random audio file from SFX directory"""
        try:
            all_files = [f for f in os.listdir(SFX_DIR) if f.lower().endswith(('.wav', '.mp3', '.flac', '.aiff', '.ogg'))]
            if not all_files: return None
            
            chosen = random.choice(all_files)
            full_path = os.path.join(SFX_DIR, chosen)
            
            # --- LOG: SELECTION ---
            print(f"      🎲 Selected SFX: {chosen}", flush=True)
            
            return full_path
        except Exception as e:
            print(f"      ❌ SFX Selection Error: {e}")
            return None

    def run(self, queries, video_format=None, out_path=None):
        raw_arg = queries[0] if isinstance(queries, list) and queries else queries
        if not raw_arg: raw_arg = self.config.get('input_file')
        if not raw_arg: print("❌ Error: No JSON input."); return False
        filename = os.path.basename(raw_arg)
        organized_path = os.path.join(CUSTOM_INPUT_DIR, filename)
        final_path = organized_path if os.path.exists(organized_path) else raw_arg
        if not os.path.exists(final_path): print(f"❌ Error: File not found: {final_path}"); return False
        print(f"🎬 Starting Intelligent Broadcast from: {os.path.basename(final_path)}", flush=True)
        self.run_story(final_path)
        return True

    def load_json_input(self, filepath):
        try:
            with open(filepath, 'r') as f: return json.load(f)
        except: return None

    def generate_hook_via_qwen(self, headline, summary):
        print(f"   🧠 [Qwen] Generating hook for: '{headline[:30]}...'", flush=True)
        try:
            prompt = f"Act as a TV News Producer. Turn this headline into a dramatic, short question (max 6 words) to hook viewers. Headline: {headline}. Details: {summary}."
            response = utils.query_local_llm(prompt, max_words=10, temperature=0.7)
            if response:
                clean = response.replace('"', '').strip()
                if not clean.endswith('?'): clean += "?"
                return clean
        except: pass
        return f"What does {headline.split()[0]} update mean?"

    def generate_split_audio(self, hook_text, body_text, idx):
        hook_path = os.path.join(audio_generator.dirs["voiceovers"], f"hook_{idx}.mp3")
        body_path = os.path.join(audio_generator.dirs["voiceovers"], f"body_{idx}.mp3")
        
        audio_generator.generate_single_voiceover(hook_text, hook_path)
        audio_generator.generate_single_voiceover(body_text, body_path)
        
        clip_hook = self.sanitize_audio(hook_path)
        clip_body = self.sanitize_audio(body_path)
        
        if not clip_hook or not clip_body: return None, 2.0
        
        silence_path = os.path.join(self.wav_dir, "silence_0.2.wav")
        if not os.path.exists(silence_path): self.make_silent_wave(silence_path, duration=0.2)
        silence = AudioFileClip(silence_path)
        
        combined = concatenate_audioclips([clip_hook, silence, clip_body])
        split_time = clip_hook.duration 
        
        return combined, split_time

    def run_story(self, json_path):
        raw_input = self.load_json_input(json_path)
        if raw_input is None: return

        raw_list = raw_input if isinstance(raw_input, list) else (raw_input.get("data") or raw_input.get("news_items") or raw_input.get("items", []))
        company = raw_input.get("company_name", "Update") if isinstance(raw_input, dict) else "Update"

        slides_data = []
        slides_data.append({'ticker': 'LIVE', 'headline': 'BREAKING NEWS', 'summary': f"Important updates for {company}.", 'theme': 'breaking_bar', 'is_intro': True})

        for entry in raw_list:
            headline = entry.get('headline', '')
            summary = entry.get('summary', '')
            hook = entry.get('hook')
            if not hook: hook = self.generate_hook_via_qwen(headline, summary)
            
            entry['hook_text'] = hook
            entry['is_content'] = True
            slides_data.append(entry)

        slides_data.append({'ticker': 'SUBSCRIBE', 'headline': 'STAY TUNED', 'summary': 'Subscribe now for daily updates.', 'theme': 'market_dashboard', 'is_outro': True})

        clips = []
        print(f"\n📊 Rendering {len(slides_data)} Segments...", flush=True)
        
        for idx, item in enumerate(slides_data):
            try:
                split_time = 2.0 
                
                if item.get('is_content'):
                    print(f"   🎙️ Seg {idx}: Punchy Split Audio...", flush=True)
                    audio_clip, split_time = self.generate_split_audio(item['hook_text'], item['summary'], idx)
                    if not audio_clip: continue
                    full_script = f"{item['hook_text']} ... {item['summary']}"
                else:
                    script = item['summary']
                    filename = f"std_{idx}_{random.randint(100,999)}.mp3"
                    path = os.path.join(audio_generator.dirs["voiceovers"], filename)
                    audio_generator.generate_single_voiceover(script, path)
                    audio_clip = self.sanitize_audio(path)
                    if not audio_clip: continue
                    full_script = script

                duration = audio_clip.duration + 0.5
                
                forced_theme = item.get('theme')
                theme_key = forced_theme if (forced_theme and forced_theme in THEMES) else random.choice(VALID_RANDOM_THEMES)
                if not forced_theme: print(f"      🎨 Auto-Theme: {theme_key}")

                bg_path = compositor.get_smart_background_path(
                    item.get('ticker','NEWS'), 
                    item.get('headline',''), 
                    THEMES[theme_key]['bg_mode'], 
                    item.get('image')
                )
                
                if bg_path and bg_path.lower().endswith('.mp4'):
                    try:
                        v_bg = VideoFileClip(bg_path)
                        if v_bg.duration < duration: v_bg = v_bg.loop(duration=duration)
                        else: v_bg = v_bg.subclip(0, duration)
                        w, h = v_bg.size
                        target_ratio = 1080/1920
                        if w/h > target_ratio:
                            new_w = int(h * target_ratio); center_x = w // 2
                            v_bg = v_bg.crop(x1=center_x - new_w//2, width=new_w, height=h)
                        bg_clip = v_bg.resize(height=1920)
                    except: bg_clip = ColorClip(size=(1080,1920), color=(20,20,30)).set_duration(duration)
                else:
                    bg_clip = effects.apply_cinematic_effect(bg_path, duration, (1080, 1920))

                if item.get('is_content'):
                    safe_split = max(1.0, split_time)
                    if safe_split > duration - 1.5: safe_split = duration / 2
                    
                    print(f"      ⏱️ Sync: Transition at {safe_split:.2f}s", flush=True)
                    
                    hook_img = compositor.render_hook_only_layer(item['hook_text'])
                    hook_path = os.path.join(TMP_DIR, f"hook_{idx}.png")
                    hook_img.save(hook_path)
                    
                    news_img = compositor.render_overlay_layer(item, theme_key)
                    news_path = os.path.join(TMP_DIR, f"news_{idx}.png")
                    news_img.save(news_path)
                    
                    hook_clip = ImageClip(hook_path).set_start(0).set_duration(safe_split).set_position("center")
                    hook_clip = self.animate_popup(hook_clip, duration=0.5)
                    
                    news_clip = ImageClip(news_path).set_start(safe_split).set_duration(duration - safe_split).set_position("center")
                    news_clip = news_clip.crossfadein(0.3)
                    
                    final_layers = [bg_clip, hook_clip, news_clip]
                else:
                    overlay_img = compositor.render_overlay_layer(item, theme_key)
                    overlay_path = os.path.join(TMP_DIR, f"ov_{idx}.png")
                    overlay_img.save(overlay_path)
                    overlay_clip = ImageClip(overlay_path).set_duration(duration)
                    final_layers = [bg_clip, overlay_clip]

                sub_clip = self.create_subtitle_clip(full_script, duration, (1080, 1920))
                final_layers.append(sub_clip)

                video_clip = CompositeVideoClip(final_layers).set_duration(duration)
                
                # --- SFX MIXING (FIXED) ---
                final_audio_layers = [audio_clip]
                
                if item.get('is_content'):
                    sfx_path = self.get_random_sfx() # Use the new robust selector
                    if sfx_path:
                        # Sanitize the SFX first
                        sfx_clip = self.sanitize_audio(sfx_path)
                        if sfx_clip:
                            print(f"      🎵 SFX Added at {safe_split:.2f}s", flush=True)
                            sfx_clip = sfx_clip.volumex(0.4).set_start(safe_split)
                            final_audio_layers.append(sfx_clip)
                    else:
                        print("      ⚠️ No SFX files available.", flush=True)

                video_clip = video_clip.set_audio(CompositeAudioClip(final_audio_layers))
                clips.append(video_clip)
            
            except Exception as e:
                print(f"      ❌ Seg {idx} Error: {e}", flush=True)
                import traceback; traceback.print_exc()

        # 3. ASSEMBLY
        if clips:
            final_video = concatenate_videoclips(clips, method="compose")
            if os.path.exists(MUSIC_DIR):
                music_files = [f for f in os.listdir(MUSIC_DIR) if f.endswith('.mp3')]
                if music_files:
                    bgm_path = os.path.join(MUSIC_DIR, random.choice(music_files))
                    bgm = self.sanitize_audio(bgm_path)
                    if bgm:
                        if bgm.duration < final_video.duration: bgm = bgm.audio_loop(duration=final_video.duration)
                        else: bgm = bgm.subclip(0, final_video.duration)
                        final_video = final_video.set_audio(CompositeAudioClip([final_video.audio, bgm.volumex(0.12)]))

            out_file = os.path.join(OUTPUT_DIR, f"Broadcast_{os.path.splitext(os.path.basename(json_path))[0]}.mp4")
            final_video.write_videofile(out_file, fps=24, codec="libx264", audio_codec="aac", threads=4, logger='bar')
            print(f"🎉 SUCCESS: {out_file}", flush=True)
            for c in clips: c.close()

    def animate_popup(self, clip, duration=0.6):
        def resize_func(t):
            if t >= duration: return 1.0
            if t < 0.4: return max(0.01, (t / 0.4) * 1.05)
            progress = (t - 0.4) / (duration - 0.4)
            return 1.05 - (0.05 * progress)
        return clip.resize(resize_func).set_position("center")

    def create_subtitle_clip(self, text, duration, size):
        W, H = size
        img = Image.new("RGBA", size, (0,0,0,0))
        draw = ImageDraw.Draw(img)
        font_path = os.path.join(ASSETS_DIR, "fonts", "Montserrat-Bold.ttf")
        font = core.load_font(font_path, 40)
        margin = int(W * 0.1)
        lines = core.wrap_text_pil(text, font, W - (margin*2))
        line_h = 50
        box_h = (len(lines) * line_h) + 40
        box_y = H - 580 
        draw.rounded_rectangle([margin-20, box_y, W-margin+20, box_y+box_h], radius=15, fill=(0,0,0,200))
        curr_y = box_y + 20
        for line in lines:
            draw.text((W/2, curr_y), line, font=font, fill="#FFD700", anchor="mt")
            curr_y += line_h
        return ImageClip(np.array(img)).set_duration(duration)