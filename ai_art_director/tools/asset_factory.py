import os
from PIL import Image, ImageDraw, ImageFilter
from ai_art_director.config import ASSETS_DIR

THEMES_DIR = os.path.join(ASSETS_DIR, "themes")

def setup_dir(name):
    path = os.path.join(THEMES_DIR, name)
    os.makedirs(path, exist_ok=True)
    return path

def draw_breaking_bar():
    """Red Banner (CNBC) - Precision Alignment Fix"""
    path = setup_dir("breaking_bar")
    img = Image.new("RGBA", (1080, 1920), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    # 1. Red Headline Bar (The Big Strip)
    # Y = 920 to 1080
    draw.polygon([(0, 920), (1080, 920), (1080, 1080), (0, 1080)], fill="#cc0000")
    
    # 2. White Sub Bar (The Details Strip)
    # Y = 1080 to 1250
    draw.polygon([(0, 1080), (1080, 1080), (1080, 1250), (0, 1250)], fill="white")
    
    # 3. Ticker Badge (The Small "LIVE" or "TICKER" Box)
    # Fix: Placed at Y=840 to 910. Matches config 'ticker' y=880 (center)
    # X=50 to 350 (Left aligned)
    draw.rounded_rectangle([50, 840, 350, 910], radius=10, fill="#cc0000")
    
    # Add a small white accent line on the badge
    draw.line([(60, 845), (340, 845)], fill="white", width=2)
    
    img.save(f"{path}/plate.png")
    print("✅ 'Breaking News' Template Updated")


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
    """
    REDESIGN: TV Monitor Style (Gold + Rounded Fix)
    """
    path = setup_dir("glass_stack")
    W, H = 1080, 1920
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    # --- 1. TV FRAME ---
    screen_x, screen_y = 50, 600
    screen_w, screen_h = 980, 700
    border_thick = 15
    radius = 40
    
    # Drop Shadow
    draw.rounded_rectangle(
        [screen_x+20, screen_y+20, screen_x+screen_w+20, screen_y+screen_h+20],
        radius=radius, fill=(0,0,0,150)
    )
    
    # Gold Gradient Border
    gold_shades = ["#C5A059", "#E6C975", "#F7D98B", "#D4AF37", "#AA863A"]
    for i in range(border_thick):
        color = gold_shades[i % len(gold_shades)]
        draw.rounded_rectangle(
            [screen_x+i, screen_y+i, screen_x+screen_w-i, screen_y+screen_h-i],
            radius=radius-i, outline=color, width=1
        )
    
    # --- 2. INNER SCREEN (Rounded Mask Fix) ---
    inner_x = screen_x + border_thick
    inner_y = screen_y + border_thick
    inner_w = screen_w - (border_thick*2)
    inner_h = screen_h - (border_thick*2)
    
    # Create a temporary image for the screen content
    screen_content = Image.new("RGBA", (inner_w, inner_h), (0,0,0,0))
    sc_draw = ImageDraw.Draw(screen_content)
    
    # Draw Gradient on temp image
    for i in range(inner_h):
        ratio = i / inner_h
        r = int(208 - (ratio * 55)) 
        sc_draw.line([(0, i), (inner_w, i)], fill=(r, 0, 0))
    
    # Draw White Header Strip on temp image
    header_h = 150 # Made taller
    sc_draw.rectangle([0, 40, inner_w, 40 + header_h], fill="white")
    
    # Red Badges
    badge_w = 300
    sc_draw.polygon([(0, 40), (badge_w, 40), (badge_w-30, 40+header_h), (0, 40+header_h)], fill="#cc0000")
    sc_draw.polygon([(inner_w-badge_w+30, 40), (inner_w, 40), (inner_w, 40+header_h), (inner_w-badge_w, 40+header_h)], fill="#cc0000")

    # Create Rounded Mask for the screen
    mask = Image.new("L", (inner_w, inner_h), 0)
    mask_draw = ImageDraw.Draw(mask)
    # Radius slightly smaller than frame to fit snugly
    mask_draw.rounded_rectangle([0, 0, inner_w, inner_h], radius=radius-border_thick, fill=255)
    
    # Paste Screen content onto Main Image using Mask
    img.paste(screen_content, (inner_x, inner_y), mask)

    # --- 3. GLOSS (Reflection) ---
    gloss = Image.new("RGBA", (W, H), (0,0,0,0))
    g_draw = ImageDraw.Draw(gloss)
    # Mask gloss to inner area too
    g_draw.polygon(
        [(inner_x, inner_y), (inner_x+inner_w, inner_y), (inner_x+inner_w, inner_y + inner_h*0.4), (inner_x, inner_y + inner_h*0.3)],
        fill=(255, 255, 255, 30)
    )
    img = Image.alpha_composite(img, gloss)
    
    # --- 4. TICKER BOX (Top Center) ---
    sub_w, sub_h = 400, 80
    sx = (W - sub_w) // 2
    sy = screen_y - 60 
    
    draw = ImageDraw.Draw(img) # Re-init
    draw.rectangle([sx, sy, sx+sub_w, sy+sub_h], fill="#cc0000", outline="white", width=4)
    
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
    """
    REDESIGN: Newspaper Pop-up with Realistic Depth.
    """
    path = setup_dir("vertical_ticker")
    W, H = 1080, 1920
    
    # --- PART A: Background (Unchanged) ---
    bg_img = Image.new("RGB", (W, H), "#4a0505")
    bg_draw = ImageDraw.Draw(bg_img)
    for y in range(H):
        ratio = y / H
        if ratio < 0.5:
            r = int(123 + (40 * (ratio * 2)))
            g = int(13 + (20 * (ratio * 2)))
            b = 13
        else:
            r = int(163 - (100 * ((ratio-0.5) * 2)))
            g = int(22 - (20 * ((ratio-0.5) * 2)))
            b = 5
        bg_draw.line([(0, y), (W, y)], fill=(r, g, b))
    bg_img.save(f"{path}/bg.png")
    
    # --- PART B: The Speech Bubble Plate ---
    # We use a larger canvas to handle blur bleed
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    
    # Box Coordinates
    bx, by = 100, 480
    bw, bh = 880, 750 
    radius = 30
    
    # --- STEP 1: REALISTIC SHADOW GENERATION ---
    # Create a separate mask for the shadow
    shadow_layer = Image.new("RGBA", (W, H), (0,0,0,0))
    s_draw = ImageDraw.Draw(shadow_layer)
    
    # Draw the shape in Black on the shadow layer
    # Main Box
    s_draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=radius, fill="black")
    # Tail
    tail_coords = [(bx + 80, by + bh - 5), (bx + 20, by + bh + 80), (bx + 250, by + bh - 5)]
    s_draw.polygon(tail_coords, fill="black")
    
    # Apply Blur
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=20))
    
    # Paste Shadow onto main image (Offset by +15px X, +25px Y)
    # Reducing opacity to 100/255 for a subtle depth
    r, g, b, a = shadow_layer.split()
    a = a.point(lambda i: i * 0.6) # 60% opacity
    shadow_layer.putalpha(a)
    
    img.paste(shadow_layer, (15, 25), shadow_layer)

    # --- STEP 2: DRAW THE PAPER ON TOP ---
    draw = ImageDraw.Draw(img)

    # Tail (Pointer) - Draw first so it merges with box
    draw.polygon(tail_coords, fill="#F5F5F5")

    # Main Paper Box
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=radius, fill="#F5F5F5")
    
    # Styling (Black Bar & Lines)
    line_y = by + 140
    draw.line([(bx + 40, line_y), (bx + bw - 40, line_y)], fill="black", width=5)
    draw.line([(bx + 40, line_y + 12), (bx + bw - 40, line_y + 12)], fill="black", width=2)
    
    # Headline Bar
    bar_y = line_y + 40
    bar_h = 150
    draw.rectangle([bx + 40, bar_y, bx + bw - 40, bar_y + bar_h], fill="#1a1a1a")
    
    # Columns
    txt_y_start = by + bh - 100
    col_w = (bw - 100) / 2
    for i in range(3):
        ly = txt_y_start + (i*15)
        draw.line([(bx+40, ly), (bx+40+col_w-20, ly)], fill="#CCCCCC", width=2)
        draw.line([(bx+40+col_w+10, ly), (bx+40+col_w+10+col_w, ly)], fill="#CCCCCC", width=2)

    img.save(f"{path}/plate.png")
    print("✅ Newspaper Pop-up (With Deep Shadow) Created")

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