# audio_generator.py
# v20.2.6 - Handles all audio generation and fallbacks

import os
import time
import traceback
import subprocess
import sys
from typing import Dict, List, Optional
import utils

def generate_single_voiceover(text, output_path, lang='en'):
    """Generate single voiceover using tts_worker"""
    try:
        safe_text = text.replace('"', '\\"').replace("'", "\\'")
        
        cmd = [
            sys.executable, 
            "tts_worker.py",
            f'"{safe_text}"',
            f'"{output_path}"',
            "--lang", lang
        ]
        
        result = subprocess.run(
            " ".join(cmd), 
            shell=True,
            capture_output=True, 
            text=True, 
            timeout=120
        )
        
        if result.returncode == 0:
            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                return True
            else:
                print(f"      - ❌ TTS file created but is empty: {output_path}")
                return False
        else:
            print(f"      - ❌ TTS worker failed with return code: {result.returncode}")
            if result.stderr:
                print(f"      - TTS stderr: {result.stderr[:200]}...")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"      - ❌ TTS worker timeout after 120 seconds")
        return False
    except Exception as e:
        print(f"      - ❌ TTS worker error: {e}")
        return False

def generate_segmented_voiceover(audio_script_parts, lang='en'):
    """Generate voiceover audio files for each script segment"""
    try:
        audio_paths = {}
        script_dir = utils.get_script_dir()
        tmp_dir = os.path.join(script_dir, "outputs", "tmp")
        
        os.makedirs(tmp_dir, exist_ok=True)
        
        # Test if directory is writable
        try:
            test_file = os.path.join(tmp_dir, "test_write.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            print(f"❌ CRITICAL: Cannot write to tmp directory: {e}")
            print(f"   Please check permissions for: {tmp_dir}")
            return create_emergency_fallback_audio()
        
        print(f"   -> Generating {len(audio_script_parts)} voiceovers in {lang}...")
        
        success_count = 0
        for key, text in audio_script_parts.items():
            if not text or not text.strip():
                print(f"⚠️  Skipping empty audio script for: {key}")
                continue
                
            output_path = os.path.join(tmp_dir, f"vo_{key}.mp3")
            
            print(f"      - Generating: {key} ({len(text)} chars)")
            
            success = generate_single_voiceover(text, output_path, lang)
            
            if success and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                audio_paths[key] = output_path
                success_count += 1
                print(f"      ✅ Audio saved: {os.path.basename(output_path)} ({file_size} bytes)")
            else:
                print(f"❌ FAILED to generate audio for: {key}")
                if create_proper_silent_audio(output_path, duration=4.0):
                    audio_paths[key] = output_path
                    print(f"      ✅ Created silent fallback for: {key}")
        
        print(f"   ✅ Generated {success_count}/{len(audio_script_parts)} audio segments successfully")
        return audio_paths
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR in voiceover generation: {e}")
        traceback.print_exc()
        return create_emergency_fallback_audio()

def create_proper_silent_audio(output_path, duration=4.0):
    """Create properly formatted silent audio"""
    try:
        import subprocess
        
        cmd = [
            'ffmpeg',
            '-f', 'lavfi',
            '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
            '-t', str(duration),
            '-c:a', 'libmp3lame',
            '-b:a', '128k',
            '-y',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            if file_size > 100:
                return True
            else:
                print(f"      - ❌ Silent audio file too small: {file_size} bytes")
                return False
        else:
            print(f"      - ❌ FFmpeg silent audio failed: {result.stderr}")
            return create_basic_silent_wav(output_path, duration)
            
    except Exception as e:
        print(f"      - ❌ FFmpeg silent audio failed: {e}")
        return create_basic_silent_wav(output_path, duration)

def create_basic_silent_wav(output_path, duration=4.0):
    """Create basic WAV file as fallback"""
    try:
        import wave
        import struct
        
        wav_path = output_path.replace('.mp3', '.wav')
        
        sample_rate = 44100
        num_channels = 2
        sample_width = 2
        num_frames = int(sample_rate * duration)
        
        with wave.open(wav_path, 'w') as wav_file:
            wav_file.setnchannels(num_channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.setnframes(num_frames)
            
            silent_frame = struct.pack('<hh', 0, 0)
            for _ in range(num_frames):
                wav_file.writeframes(silent_frame)
        
        try:
            import subprocess
            cmd = [
                'ffmpeg', '-i', wav_path, '-codec:a', 'libmp3lame', 
                '-b:a', '128k', '-y', output_path
            ]
            subprocess.run(cmd, capture_output=True, timeout=10)
            
            if os.path.exists(wav_path):
                os.remove(wav_path)
                
            if os.path.exists(output_path):
                return True
            else:
                os.rename(wav_path, output_path.replace('.mp3', '.wav'))
                return False
                
        except:
            if os.path.exists(wav_path):
                os.rename(wav_path, output_path.replace('.mp3', '.wav'))
                return False
            return False
            
    except Exception as e:
        print(f"      - ❌ WAV silent audio failed: {e}")
        return create_minimal_audio_fallback(output_path)

def create_minimal_audio_fallback(output_path):
    """Absolute minimal fallback"""
    try:
        script_dir = utils.get_script_dir()
        tmp_dir = os.path.join(script_dir, "outputs", "tmp")
        if os.path.exists(tmp_dir):
            for file in os.listdir(tmp_dir):
                if file.startswith('vo_') and file.endswith('.mp3'):
                    source_path = os.path.join(tmp_dir, file)
                    if os.path.getsize(source_path) > 100:
                        import shutil
                        shutil.copy2(source_path, output_path)
                        print(f"      - ✅ Copied working audio: {file}")
                        return True
        
        with open(output_path, 'wb') as f:
            f.write(b'FAKE_AUDIO')
        print(f"      - ⚠️  Created placeholder file (will be skipped)")
        return False
        
    except Exception as e:
        print(f"      - 💥 All audio fallbacks failed: {e}")
        return False

def create_emergency_fallback_audio():
    """Create emergency fallback audio files"""
    script_dir = utils.get_script_dir()
    tmp_dir = os.path.join(script_dir, "outputs", "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    
    fallback_paths = {}
    for key in ['intro', 'cta']:
        output_path = os.path.join(tmp_dir, f"vo_{key}.mp3")
        if create_proper_silent_audio(output_path, duration=3.0):
            fallback_paths[key] = output_path
        else:
            print(f"      - ⚠️  Could not create fallback for: {key}")
    
    return fallback_paths
