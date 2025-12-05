# subtitle_generator.py - ENHANCED VERSION
# v20.2.8 - Complete Whisper speech-to-text integration

import whisper
import os
from typing import List, Tuple

class SubtitleGenerator:
    def __init__(self):
        self.model = None
        
    def load_model(self):
        """Load Whisper model on demand"""
        if self.model is None:
            try:
                print("      - 🎙️ Loading Whisper model for speech-to-text...")
                self.model = whisper.load_model("base")
                print("      - ✅ Whisper model loaded successfully")
            except Exception as e:
                print(f"      - ❌ Failed to load Whisper model: {e}")
                print("      - 💡 Install Whisper: pip install openai-whisper")
                return False
        return True

def generate_subtitles(audio_path):
    """Generate subtitles using Whisper speech-to-text"""
    try:
        print(f"      - 📝 Generating subtitles for: {audio_path}")
        
        if not os.path.exists(audio_path):
            print(f"      - ❌ Audio file not found: {audio_path}")
            return []
        
        # Initialize Whisper
        generator = SubtitleGenerator()
        if not generator.load_model():
            print("      - ⚠️  Using fallback subtitle generation")
            return generate_subtitles_from_script_fallback(audio_path)
        
        # Transcribe audio with timestamps
        result = generator.model.transcribe(audio_path, word_timestamps=True)
        
        # Convert to subtitle format
        subtitles = []
        for segment in result['segments']:
            start = segment['start']
            end = segment['end']
            text = segment['text'].strip()
            
            if text and len(text) > 1:  # Filter out very short segments
                subtitles.append(((start, end), text))
        
        print(f"      - ✅ Generated {len(subtitles)} subtitle segments using Whisper")
        return subtitles
        
    except Exception as e:
        print(f"      - ❌ Whisper subtitle generation failed: {e}")
        return generate_subtitles_from_script_fallback(audio_path)

def generate_subtitles_from_script_fallback(audio_path):
    """Fallback subtitle generation when Whisper fails"""
    print("      - 🔄 Using fallback subtitle generation")
    # Return empty for now - you could implement Azure STT here
    return []

def generate_subtitles_from_script(audio_script_parts, total_duration):
    """Generate subtitles from the script text (simplified approach)"""
    try:
        subtitles = []
        current_time = 0.0
        
        # Estimate timing based on text length (rough approximation)
        for key, text in audio_script_parts.items():
            if text and len(text) > 10:  # Only for substantial text
                # Rough duration estimation: 4 words per second
                word_count = len(text.split())
                duration = max(2.0, min(8.0, word_count / 4.0))
                
                subtitles.append(((current_time, current_time + duration), text))
                current_time += duration
            else:
                # Short texts get 2 seconds
                if text and len(text.strip()) > 0:
                    subtitles.append(((current_time, current_time + 2.0), text))
                    current_time += 2.0
        
        print(f"      - ✅ Generated {len(subtitles)} subtitle segments from script")
        return subtitles
        
    except Exception as e:
        print(f"      - ❌ Script-based subtitle generation failed: {e}")
        return []
