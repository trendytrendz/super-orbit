import os
import time
import traceback
import subprocess
import sys
import shutil
import random
from typing import Dict, List, Optional
from pathlib import Path

from . import utils
from . import config 

# Import Hindi translator
try:
    from .hindi_translator import translate_script_to_hindi
except ImportError:
    print("⚠️  hindi_translator.py not available - Hindi support limited")
    def translate_script_to_hindi(english_script_parts):
        return english_script_parts

class AudioGenerator:
    """Enhanced audio generator with robust error handling and natural speech"""
    
    def __init__(self):
        self.audio_cache = {}
        self.setup_audio_directories()
    
    def setup_audio_directories(self):
        """Ensure audio directories exist using CONFIG ABSOLUTE PATHS"""
        self.dirs = {
            "voiceovers": str(config.AUDIO_VOICEOVERS_DIR),
            "cache": str(config.AUDIO_CACHE_DIR),
            "fallbacks": str(config.AUDIO_FALLBACKS_DIR)
        }
        
        for d in self.dirs.values():
            os.makedirs(d, exist_ok=True)
    
    def generate_single_voiceover(self, text: str, output_path: str, lang: str = 'en', speed_adj=None) -> bool:
        """
        Generates TTS via Worker.
        PRIORITY 3: Accepts speed_adj (e.g. "+20%") for Hook/Body variance.
        """
        try:
            if not text or not text.strip():
                return self.create_proper_silent_audio(output_path, duration=3.0)
            
            script_dir = str(config.SRC_DIR)
            tts_worker_path = os.path.join(script_dir, "tts_worker.py")
            
            # CONFIG
            vc = config.get_voice_for_lang(lang)
            edge_voice = vc.get("edge_voice", "en-US-AriaNeural") 
            
            # --- RATE LOGIC ---
            # If specific override provided, use it. Else use config default.
            edge_rate = speed_adj if speed_adj else vc.get("edge_rate", "+0%")
            
            cmd = [
                sys.executable, tts_worker_path, 
                text, output_path, 
                "--lang", lang,
                "--edge_voice", edge_voice,
                "--edge_rate", edge_rate
            ]
            
            # RUN WITH CAPTURE
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                return True
            else:
                # print(f"      - ❌ TTS FAILED. RetCode: {result.returncode}")
                return self.create_proper_silent_audio(output_path, duration=4.0)
                
        except Exception as e:
            print(f"      - ❌ Exception: {e}")
            return self.create_proper_silent_audio(output_path, duration=4.0)
    
    def generate_segmented_voiceover(self, audio_script_parts: Dict[str, str], lang: str = 'en') -> Dict[str, str]:
        audio_paths = {}
        print(f"   -> 🎵 Generating {len(audio_script_parts)} voiceovers...")
        
        for key, text in audio_script_parts.items():
            safe_key = "".join(c for c in key if c.isalnum() or c in ('_', '-')).rstrip()
            filename = f"vo_{safe_key}.mp3"
            output_path = os.path.join(self.dirs["voiceovers"], filename)
            
            cache_key = f"{lang}_{hash(text)}"
            cache_path = os.path.join(self.dirs["cache"], f"{cache_key}.mp3")

            if os.path.exists(cache_path) and os.path.getsize(cache_path) > 500:
                shutil.copy2(cache_path, output_path)
                audio_paths[key] = output_path
                continue
            
            if self.generate_single_voiceover(text, output_path, lang):
                audio_paths[key] = output_path
                if os.path.getsize(output_path) > 2000:
                     shutil.copy2(output_path, cache_path)
        return audio_paths
    
    def create_proper_silent_audio(self, output_path: str, duration: float = 3.0) -> bool:
        """Create a proper silent audio file using ffmpeg"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
                '-t', str(duration), '-c:a', 'libmp3lame', '-b:a', '128k', '-y', output_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                return True
            return self.create_emergency_fallback_audio(output_path)
        except Exception:
            return self.create_emergency_fallback_audio(output_path)
    
    def create_emergency_fallback_audio(self, output_path: str) -> bool:
        """Create emergency fallback audio when all else fails"""
        try:
            import wave, struct
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with wave.open(output_path, 'wb') as wav_file:
                wav_file.setnchannels(1); wav_file.setsampwidth(2); wav_file.setframerate(22050)
                wav_file.writeframes(struct.pack('<h', 0) * 22050 * 3)
            return True
        except: return False
    
    def cleanup_audio_cache(self):
        pass # Keep for debugging

# Global Instance (Optional, for backward compat)
audio_generator = AudioGenerator()

BG_TRACKS = [
    "breaking_news_intro.mp3", # Urgent
    "tech_daily.mp3",          # Modern
    "market_floor.mp3"         # Ambient
]

def get_random_bgm():
    """Pick a random background track for the video"""
    track = random.choice(BG_TRACKS)
    return os.path.join("assets/audio/bgm", track)