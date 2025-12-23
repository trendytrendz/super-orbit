#/visuals/effects.py
import os
import random
import numpy as np
from moviepy.editor import ImageClip, ColorClip, CompositeVideoClip
from PIL import Image
from .. import config

def apply_cinematic_effect(img_path, duration, size):
    """
    Applies motion effects (Pan/Zoom) while GUARANTEEING total screen coverage
    AND strict cropping to the target size (no bleed outside frame).
    """
    target_w, target_h = size
    
    if not img_path or not os.path.exists(img_path):
        return ColorClip(size=size, color=(10, 20, 40), duration=duration)

    try:
        # 1. Load Image
        pil_img = Image.open(img_path).convert("RGBA")
        iw, ih = pil_img.size
        
        # 2. Scale to COVER (No black bars)
        # We find the scale factor that ensures BOTH dimensions are >= target
        scale = max(target_w / iw, target_h / ih)
        
        # Add 15% buffer for movement
        scale *= 1.15
        
        new_w = int(iw * scale)
        new_h = int(ih * scale)
        
        pil_resized = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Create base clip from the large image
        clip = ImageClip(np.array(pil_resized)).set_duration(duration)
        
        # Randomize Effect
        moves = ['pan_horizontal', 'slow_zoom_in']
        # If image is very wide relative to target, prefer Pan
        aspect_ratio = new_w / new_h
        target_aspect = target_w / target_h
        
        if aspect_ratio > target_aspect * 1.2:
            move = 'pan_horizontal'
        else:
            move = 'slow_zoom_in'

        # --- OPTION A: PAN HORIZONTAL ---
        if move == 'pan_horizontal':
            # Center vertically
            y_center = -(new_h - target_h) // 2
            
            # Allowable X movement
            max_x_offset = new_w - target_w
            
            # Random direction
            if random.random() > 0.5:
                # Left -> Right
                start_x = -int(max_x_offset * 0.1)
                end_x = -int(max_x_offset * 0.9)
            else:
                start_x = -int(max_x_offset * 0.9)
                end_x = -int(max_x_offset * 0.1)
                
            # Apply Motion
            clip = clip.set_position(lambda t: (
                int(start_x + (end_x - start_x) * (t / duration)), 
                y_center
            ))

        # --- OPTION B: SLOW ZOOM IN ---
        else:
            # Start centered
            # The clip is already 1.15x larger than target.
            # We will start at scale 1.0 (relative to clip size) and grow to 1.05
            # Center crop happens automatically if set_position is center relative to a CompositeVideoClip container
            # BUT since we are returning a raw clip, we must be careful.
            
            # Best approach for MoviePy Zoom: 
            # Resize logic on the large clip, keeping it centered.
            clip = clip.set_position('center').resize(lambda t: 1 + 0.03 * t)

        # --- CRITICAL FINAL STEP: CROP TO VIEWPORT ---
        # We must wrap this moving clip in a CompositeVideoClip of the exact target size
        # This forces the "viewport" to be 1080x1920, cutting off any bleed.
        final_comp = CompositeVideoClip([clip], size=size).set_duration(duration)
        
        return final_comp

    except Exception as e:
        print(f"      ⚠️ Effect Error: {e}")
        # Static Fallback (Strict Crop)
        return ImageClip(img_path).resize(height=target_h).crop(x1=0, y1=0, width=target_w, height=target_h).set_duration(duration)

# --- COMPATIBILITY ALIASES ---
create_pan_zoom_clip = apply_cinematic_effect

def apply_random_animation(clip, start_time, slide_duration, size):
    """Legacy wrapper."""
    return clip.set_start(start_time).set_duration(slide_duration).crossfadein(0.5)
