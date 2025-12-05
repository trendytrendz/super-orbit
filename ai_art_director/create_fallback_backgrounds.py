# create_fallback_backgrounds.py
import os
from PIL import Image, ImageDraw

def create_fallback_backgrounds():
    output_dir = "assets/fallback_backgrounds"
    os.makedirs(output_dir, exist_ok=True)
    
    colors = [
        ("#1a237e", "#283593"),  # Dark blue gradient
        ("#00695c", "#004d40"),  # Dark teal gradient  
        ("#4a148c", "#6a1b9a"),  # Purple gradient
        ("#b71c1c", "#c62828"),  # Red gradient
        ("#01579b", "#0277bd"),  # Blue gradient
    ]
    
    size = (1920, 1080)
    
    for i, (color1, color2) in enumerate(colors):
        img = Image.new('RGB', size, color1)
        draw = ImageDraw.Draw(img)
        
        # Create simple gradient effect
        for y in range(size[1]):
            ratio = y / size[1]
            r = int(int(color1[1:3], 16) * (1 - ratio) + int(color2[1:3], 16) * ratio)
            g = int(int(color1[3:5], 16) * (1 - ratio) + int(color2[3:5], 16) * ratio)
            b = int(int(color1[5:7], 16) * (1 - ratio) + int(color2[5:7], 16) * ratio)
            draw.line([(0, y), (size[0], y)], fill=(r, g, b))
        
        img.save(f"{output_dir}/background_{i+1}.jpg")
        print(f"Created {output_dir}/background_{i+1}.jpg")
    
    print(f"✅ Created {len(colors)} fallback backgrounds")

if __name__ == "__main__":
    create_fallback_backgrounds()
