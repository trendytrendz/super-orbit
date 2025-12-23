import json
import os
import random
import numpy as np
from PIL import Image, ImageDraw
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip, AudioClip, CompositeVideoClip
from ai_art_director.visuals import compositor, effects, core
from ai_art_director.audio_generator import audio_generator
from ai_art_director.config import TMP_DIR, OUTPUT_DIR, MUSIC_DIR, CUSTOM_INPUT_DIR, ASSETS_DIR
from ai_art_director import utils
from ai_art_director.visuals.theme_config import THEMES

class CustomJsonStory:
    def __init__(self, config_dict=None):
        self.config = config_dict or {}
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(TMP_DIR, exist_ok=True)

    def run(self, queries, video_format=None, out_path=None):
        raw_arg = queries[0] if isinstance(queries, list) and queries else queries
        if not raw_arg: raw_arg = self.config.get('input_file')
        
        if not raw_arg:
            print("❌ Error: No JSON input file provided.")
            return False

        filename = os.path.basename(raw_arg)
        organized_path = os.path.join(CUSTOM_INPUT_DIR, filename)
        
        if os.path.exists(organized_path): final_path = organized_path
        elif os.path.exists(raw_arg): final_path = raw_arg
        else:
            print(f"❌ Error: File not found."); return False

        print(f"🎬 Starting Cinematic Broadcast from: {os.path.basename(final_path)}")
        self.run_story(final_path)
        return True

    def load_json_input(self, filepath):
        try:
            with open(filepath, 'r') as f: return json.load(f)
        except: return None

    def get_llm_script(self, headline, summary):
        try:
            prompt = f"Write a 1-sentence TV news voiceover. Headline: {headline}. Details: {summary}"
            response = utils.query_local_llm(prompt, max_words=40, temperature=0.6)
            if response: return response.replace('"', '').strip()
        except: pass
        return f"{headline}. {summary}"

    # --- NEW: PUNCHY HOOK LOGIC ---
    def get_hook_script(self, headline, summary):
        try:
            # Prompt specifically for a question
            prompt = f"Rewrite this as a short, dramatic question for a news teaser. Content: {summary}. Keep it under 10 words."
            response = utils.query_local_llm(prompt, max_words=15, temperature=0.7)
            if response: 
                clean = response.replace('"', '').strip()
                if not clean.endswith('?'): clean += '?'
                return clean
        except: pass
        # Fallback manual question
        return f"What does {headline} mean for the market?"

    def make_silent_audio(self, filename, duration=4.0):
        try:
            make_frame = lambda t: [0] * 2
            clip = AudioClip(make_frame, duration=duration, fps=44100)
            clip.write_audiofile(filename, fps=44100, logger=None)
            return True
        except: return False

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
        box_y = H - 350
        
        draw.rounded_rectangle([margin-20, box_y, W-margin+20, box_y+box_h], radius=15, fill=(0,0,0,200))
        curr_y = box_y + 20
        for line in lines:
            draw.text((W/2, curr_y), line, font=font, fill="#FFD700", anchor="mt")
            curr_y += line_h
            
        return ImageClip(np.array(img)).set_duration(duration)

    def run_story(self, json_path):
        raw_input = self.load_json_input(json_path)
        if raw_input is None: return

        raw_list = raw_input.get("data", []) if isinstance(raw_input, dict) else raw_input
        if not raw_list: return

        # 1. BUILD PLAYLIST
        slides_data = []
        slides_data.append({'ticker': 'LIVE', 'headline': 'BREAKING NEWS', 'summary': 'Top stories developing right now.', 'theme': 'breaking_bar', 'is_intro': True})

        for entry in raw_list:
            if entry.get('hook'):
                slides_data.append({
                    'ticker': 'COMING UP', 
                    'headline': entry.get('ticker', 'STORY'), 
                    'summary': entry['hook'], 
                    'theme': 'kinetic_typo', 
                    'is_hook': True,
                    'image': entry.get('image') # Reuse image
                })
            if 'headline' in entry: slides_data.append(entry)

        slides_data.append({'ticker': 'SUBSCRIBE', 'headline': 'STAY TUNED', 'summary': 'Subscribe now for updates.', 'theme': 'market_dashboard', 'is_outro': True})

        # 2. GENERATE
        print(f"\n📊 Generating {len(slides_data)} Segments...")
        clips = []
        
        for idx, item in enumerate(slides_data):
            headline = item.get('headline', 'Update')
            summary = item.get('summary', '')
            
            # --- SCRIPT LOGIC ---
            if item.get('is_intro'): script = "Breaking news. Here are the top stories developing right now."
            elif item.get('is_outro'): script = "Thanks for watching. Don't forget to like and subscribe."
            elif item.get('is_hook'): 
                # Use the new Hook function
                script = self.get_hook_script(headline, summary)
            else: 
                script = self.get_llm_script(headline, summary)
            
            print(f"   🎙️ Slide {idx}: {script}")

            # Audio
            filename = f"broadcast_{idx}_{random.randint(100,999)}.mp3"
            audio_path = os.path.join(audio_generator.dirs["voiceovers"], filename)
            audio_generator.generate_single_voiceover(script, audio_path)
            if not os.path.exists(audio_path): self.make_silent_audio(audio_path)

            # Visuals
            try:
                forced_theme = item.get('theme')
                theme_key = forced_theme if forced_theme in THEMES else random.choice(list(THEMES.keys()))
                
                if 'headline' not in item: item['headline'] = headline
                if 'ticker' not in item: item['ticker'] = "NEWS"
                
                # Use new 'image' logic (passed as specific_image)
                bg_path = compositor.get_smart_background_path(
                    item.get('ticker'), item.get('headline'), THEMES[theme_key]['bg_mode'], item.get('image')
                )
                
                overlay_img = compositor.render_overlay_layer(item, theme_key)
                overlay_path = os.path.join(TMP_DIR, f"overlay_{idx}.png")
                overlay_img.save(overlay_path)

                # Assembly
                audio_clip = AudioFileClip(audio_path)
                duration = audio_clip.duration + 0.5
                
                bg_clip = effects.apply_cinematic_effect(bg_path, duration, (1080, 1920))
                overlay_clip = ImageClip(overlay_path).set_duration(duration)
                sub_clip = self.create_subtitle_clip(script, duration, (1080, 1920))
                
                video_clip = CompositeVideoClip([bg_clip, overlay_clip, sub_clip]).set_duration(duration)
                video_clip = video_clip.set_audio(audio_clip)
                clips.append(video_clip)
            except Exception as e:
                print(f"      ❌ Visual Fail: {e}")

        # 3. MIX
        if clips:
            final_video = concatenate_videoclips(clips, method="compose")
            
            # Music
            music_files = [f for f in os.listdir(MUSIC_DIR) if f.endswith('.mp3')] if os.path.exists(MUSIC_DIR) else []
            if music_files:
                bgm = AudioFileClip(os.path.join(MUSIC_DIR, random.choice(music_files)))
                if bgm.duration < final_video.duration: bgm = bgm.audio_loop(duration=final_video.duration)
                else: bgm = bgm.subclip(0, final_video.duration)
                final_video = final_video.set_audio(CompositeAudioClip([final_video.audio, bgm.volumex(0.15)]))

            out_file = os.path.join(OUTPUT_DIR, f"Broadcast_{os.path.splitext(os.path.basename(json_path))[0]}.mp4")
            final_video.write_videofile(out_file, fps=24, codec="libx264", audio_codec="aac", threads=4, logger='bar')
            print(f"🎉 SUCCESS: {out_file}")
            
            for c in clips: c.close()