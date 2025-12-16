import os
import numpy as np
from moviepy.editor import ImageClip, ColorClip
from PIL import Image
from .. import config

def apply_random_animation(clip, start_time, slide_duration, size):
    return clip.set_start(start_time).set_duration(slide_duration).fadein(0.5)

def create_pan_zoom_clip(duration, bg_path, size):
    bg_color = tuple(int(config.BG_COLOR.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    
    if not bg_path or not os.path.exists(bg_path): 
        return ColorClip(size=size, color=bg_color, duration=duration)
        
    try:
        img = Image.open(bg_path)
        img_w, img_h = img.size
        target_w, target_h = size
        
        # Calculate scaling to cover screen
        scale = max(target_w/img_w, target_h/img_h) * 1.1
        new_w, new_h = int(img_w * scale), int(img_h * scale)
        
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Center crop
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        img = img.crop((left, top, left + target_w, top + target_h))
        
        # Create clip with slight zoom effect
        clip = ImageClip(np.array(img)).set_duration(duration)
        return clip.resize(lambda t: 1 + 0.05 * t/duration)
        
    except Exception: 
        return ColorClip(size=size, color=bg_color, duration=duration)
