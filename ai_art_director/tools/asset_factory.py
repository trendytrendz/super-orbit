import os
from PIL import Image, ImageDraw, ImageFilter
from ai_art_director.config import ASSETS_DIR

THEMES_DIR = os.path.join(ASSETS_DIR, "themes")

def setup_dir(name):
    path = os.path.join(THEMES_DIR, name)
    os.makedirs(path, exist_ok=True)
    return path

def draw_breaking_bar():
    """Red Banner (CNBC) - RAISED POSITION"""
    path = setup_dir("breaking_bar")
    img = Image.new("RGBA", (1080, 1920), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    # SHIFT: -200px
    
    # 1. Red Headline Bar (Was 1120 -> 920)
    draw.polygon([(0, 920), (1080, 920), (1080, 1080), (0, 1080)], fill="#cc0000")
    
    # 2. White Sub Bar (Was 1280 -> 1080)
    # Height remains expanded (ends at 1250)
    draw.polygon([(0, 1080), (1080, 1080), (1080, 1250), (0, 1250)], fill="white")
    
    # 3. Ticker Badge (Was 1050 -> 850)
    draw.rounded_rectangle([50, 850, 350, 910], radius=10, fill="#cc0000")
    
    img.save(f"{path}/plate.png")

# ... (Rest of function remains identical, omitted for brevity) ...
def draw_market_dashboard():
    path = setup_dir("market_dashboard")
    img = Image.new("RGBA", (1080, 1920), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 950, 1080, 1920], fill="#0a1020")
    draw.rectangle([0, 950, 1080, 960], fill="#00ff00")
    draw.rectangle([0, 960, 1080, 1080], fill="#eeeeee")
    img.save(f"{path}/plate.png")

def draw_glass_stack():
    path = setup_dir("glass_stack")
    img = Image.new("RGBA", (1080, 1920), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([80, 320, 1000, 1000], radius=40, fill=(0,0,0,100))
    img = img.filter(ImageFilter.GaussianBlur(20))
    draw = ImageDraw.Draw(img) 
    draw.rounded_rectangle([80, 300, 1000, 980], radius=40, fill=(255,255,255,40), outline="white", width=3)
    img.save(f"{path}/plate.png")

def draw_neo_brutalist():
    path = setup_dir("neo_brutalist")
    img = Image.new("RGBA", (1080, 1920), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.rectangle([140, 370, 980, 900], fill="black")
    draw.rectangle([100, 330, 940, 860], fill="white", outline="black", width=10)
    img.save(f"{path}/plate.png")

def draw_split_deck():
    path = setup_dir("split_deck")
    img = Image.new("RGBA", (1080, 1920), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.polygon([(0, 950), (1080, 850), (1080, 1920), (0, 1920)], fill="black")
    draw.line([(0, 950), (1080, 850)], fill="yellow", width=10)
    img.save(f"{path}/plate.png")

def draw_vertical_ticker():
    path = setup_dir("vertical_ticker")
    img = Image.new("RGBA", (1080, 1920), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 1080, 1920], fill="#111111")
    draw.rectangle([40, 300, 1040, 1100], outline="#333333", width=5)
    draw.rectangle([0, 1700, 1080, 1850], fill="#000033")
    img.save(f"{path}/plate.png")

def draw_others():
    for name in ["vox_paper", "kinetic_typo", "cyber_glitch"]:
        path = setup_dir(name)
        img = Image.new("RGBA", (1080, 1920), (0,0,0,0))
        ImageDraw.Draw(img).rectangle([0, 1000, 1080, 1200], fill=(0,0,0,128))
        img.save(f"{path}/plate.png")

if __name__ == "__main__":
    draw_breaking_bar()
    draw_market_dashboard()
    draw_glass_stack()
    draw_neo_brutalist()
    draw_split_deck()
    draw_vertical_ticker()
    draw_others()