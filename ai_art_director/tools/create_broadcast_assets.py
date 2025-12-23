#ai_art_director/tools/create_broadcast_assets.py
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

ASSET_DIR = "ai_art_director/assets/templates"

def create_dir(name):
    path = os.path.join(ASSET_DIR, name)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def draw_breaking_bar():
    """
    Recreates the 'Red Banner' style (Reference 3 & 4).
    Sharp angles, gradients, high contrast.
    """
    path = create_dir("breaking_news")
    
    # 1. THE OVERLAY PLATE (1080x1920)
    img = Image.new("RGBA", (1080, 1920), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    # Top "Live" Badge
    draw.polygon([(80, 150), (300, 150), (280, 220), (60, 220)], fill="#cc0000")
    draw.text((110, 165), "BREAKING LIVE", fill="white", font_size=30) # Pseudo-code for font
    
    # Bottom Headline Bar (The Red Strip) - Moved UP (20% Rule)
    # Instead of Y=1600, we put it at Y=1200
    bar_y = 1200
    draw.polygon([(0, bar_y), (1080, bar_y), (1080, bar_y+150), (0, bar_y+150)], fill="#D00000")
    
    # The Sub-headline Bar (White Strip) underneath
    draw.polygon([(0, bar_y+150), (900, bar_y+150), (850, bar_y+250), (0, bar_y+250)], fill="white")
    
    # A "Scanline" texture overlay for TV effect
    # (Simple line loop)
    
    img.save(f"{path}/overlay.png")
    print("✅ 'Breaking News' Template Created")

def draw_market_dashboard():
    """
    Recreates the 'Euro Market Update' style (Reference 1).
    Dark gradient bottom, data boxes.
    """
    path = create_dir("market_dashboard")
    
    img = Image.new("RGBA", (1080, 1920), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    # Bottom Gradient Mesh (Dark Blue to Black)
    # We draw a solid box for now, in prod use a gradient image
    draw.rectangle([0, 960, 1080, 1920], fill="#0a1020")
    
    # The Header Strip
    draw.rectangle([0, 960, 1080, 1060], fill="#f0f0f0")
    draw.rectangle([0, 1055, 1080, 1060], fill="#00ff00") # Neon green accent line
    
    # 3 Data Container Boxes (Red/Green backgrounds)
    # We leave these transparent in the overlay, we draw them dynamically in code
    # because they need to change color based on the number (+/-).
    
    img.save(f"{path}/overlay.png")
    print("✅ 'Market Dashboard' Template Created")

if __name__ == "__main__":
    draw_breaking_bar()
    draw_market_dashboard()
