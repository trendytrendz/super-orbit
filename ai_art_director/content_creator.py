# ai_art_director/content_creator.py
# v24.2.27 - FIXED: Uses Config Absolute Paths & Removes CWD

import os
import sys
import subprocess
import shutil
from typing import Dict
from pathlib import Path
from . import config  # <--- IMPERATIVE: Uses the fixed config

# Robust import for voice_config
try:
    from . import voice_config
except ImportError:
    voice_config = None

class AudioGenerator:
    def __init__(self):
        self.setup_audio_directories()
    
    def setup_audio_directories(self):
        # 1. USE CONFIG ABSOLUTE PATHS (Fixes "Two Paths" issue)
        self.dirs = {
            "voiceovers": str(config.AUDIO_VOICEOVERS_DIR),
            "cache": str(config.AUDIO_CACHE_DIR),
            "fallbacks": str(config.AUDIO_FALLBACKS_DIR)
        }
        for d in self.dirs.values():
            os.makedirs(d, exist_ok=True)
    
    def generate_single_voiceover(self, text: str, output_path: str, lang: str = 'en') -> bool:
        # output_path is ALREADY ABSOLUTE coming from generate_segmented_voiceover
        try:
            if not text or not text.strip():
                print(f"      - ⚠️  Empty text for: {os.path.basename(output_path)}")
                return self.create_proper_silent_audio(output_path, duration=2.0)
            
            # 2. Resolve Worker Path Absolute
            script_dir = str(config.SRC_DIR)
            tts_worker_path = os.path.join(script_dir, "tts_worker.py")
            
            if not os.path.exists(tts_worker_path):
                print(f"      - ❌ Worker missing: {tts_worker_path}")
                return False

            # 3. Config
            azure_voice = "en-US-AriaNeural"
            gtts_lang = "en"
            if voice_config:
                vc = voice_config.get_voice_for_lang(lang)
                azure_voice = vc.get("azure_voice", azure_voice)
                gtts_lang = vc.get("gtts_lang", gtts_lang)
            
            # 4. Run Command
            cmd = [
                sys.executable,
                tts_worker_path,
                text,
                output_path, # Absolute path
                "--lang", lang,
                "--azure_voice", azure_voice,
                "--gtts_lang", gtts_lang,
                "--ssml" 
            ]
            
            # 5. EXECUTE WITHOUT CWD ARGUMENT (Fixes "ai_art_director/outputs" creation)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
                # cwd argument REMOVED
            )
            
            if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                # print(f"      - ✅ Generated: {os.path.basename(output_path)}")
                return True
            
            print(f"      - ❌ Worker Failed: {result.stderr}")
            return self.create_proper_silent_audio(output_path, duration=4.0)

        except Exception as e:
            print(f"      - 💥 Exception: {e}")
            return self.create_proper_silent_audio(output_path, duration=4.0)
    
    def generate_segmented_voiceover(self, audio_script_parts: Dict[str, str], lang: str = 'en') -> Dict[str, str]:
        audio_paths = {}
        print(f"   -> 🎵 Generating {len(audio_script_parts)} segments...")
        
        for key, text in audio_script_parts.items():
            safe_key = "".join(c for c in key if c.isalnum() or c in ('_', '-')).rstrip()
            filename = f"vo_{safe_key}.mp3"
            
            # 6. CONSTRUCT ABSOLUTE PATHS
            output_path = os.path.join(self.dirs["voiceovers"], filename)
            cache_path = os.path.join(self.dirs["cache"], f"{lang}_{hash(text)}.mp3")
            
            # Cache Check
            if os.path.exists(cache_path) and os.path.getsize(cache_path) > 500:
                shutil.copy2(cache_path, output_path)
                audio_paths[key] = output_path
                print(f"      - ♻️  Cached: {filename}")
                continue
            
            if self.generate_single_voiceover(text, output_path, lang):
                audio_paths[key] = output_path
                if os.path.getsize(output_path) > 2000:
                     shutil.copy2(output_path, cache_path)

        return audio_paths
    
    def create_proper_silent_audio(self, output_path: str, duration: float = 4.0) -> bool:
        try:
            cmd = ['ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-t', str(duration), '-q:a', '9', '-acodec', 'libmp3lame', '-y', output_path]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return os.path.exists(output_path)
        except: pass
        return self.create_emergency_fallback_audio(output_path)

    def create_emergency_fallback_audio(self, output_path: str) -> bool:
        try:
            import wave, struct
            with wave.open(output_path.replace('.mp3', '.wav'), 'wb') as wav_file:
                wav_file.setnchannels(1); wav_file.setsampwidth(2); wav_file.setframerate(22050)
                wav_file.writeframes(struct.pack('<h', 0) * 22050 * 3)
            return True
        except: return False

    def cleanup_audio_cache(self): pass

# Singleton
audio_generator = AudioGenerator()
generate_segmented_voiceover = audio_generator.generate_segmented_voiceover