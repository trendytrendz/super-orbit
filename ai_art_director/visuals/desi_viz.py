# ai_art_director/visuals/desi_viz.py
# v26.3.0 - Responsive Layouts & Cyber-Glass UI

import os
from PIL import Image, ImageDraw
from . import core

def render_cricket_scorecard(metrics, company_name, size, theme, out_path):
    """
    Visual: Cricket Scorecard with Responsive Math.
    Fits 3 blocks perfectly between Header and Footer.
    """
    W, H = size
    # 1. Deep Cyber Background
    img = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    # Dark Vertical Gradient
    for y in range(H):
        # #0F2027 to #203A43 (Deep Teal/Black)
        r = int(15 + (y/H)*17)
        g = int(32 + (y/H)*26)
        b = int(39 + (y/H)*28)
        draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

    font_path = theme['font']
    
    # --- RESPONSIVE LAYOUT CALCS ---
    header_h = int(H * 0.12) # 12% for Header
    footer_h = int(H * 0.08) # 8% for Footer
    
    # Available vertical space for 3 blocks
    content_top = header_h + 20
    content_bottom = H - footer_h - 20
    avail_h = content_bottom - content_top
    gap = 20
    
    # Height of one block
    block_h = int((avail_h - (gap * 2)) / 3)
    
    # 2. Header
    draw.rectangle([0, 0, W, header_h], fill=(21, 101, 192, 255)) # Corporate Blue
    draw.rectangle([0, header_h, W, header_h+6], fill="#FFD700") # Gold Line
    
    title_size = int(header_h * 0.5)
    title_font = core.load_font(font_path, title_size)
    # Shrink title
    while title_font.getlength(company_name.upper()) > W * 0.9 and title_size > 20:
        title_size -= 4
        title_font = core.load_font(font_path, title_size)
    draw.text((W/2, header_h/2), company_name.upper(), font=title_font, fill="white", anchor="mm")
    
    # 3. Data
    rev = metrics.get('Quarterly Revenue (Cr)', 0)
    prof = metrics.get('Quarterly Profit (Cr)', 0)
    margin = (prof / rev * 100) if rev else 0
    
    # 4. Glass Blocks
    def _draw_glass_block(idx, label, value, sub_label=None, val_color="white", highlight=False):
        y = content_top + (idx * (block_h + gap))
        
        # Gradient Glass Style
        # Top half lighter, bottom half darker
        bg_col = (255, 255, 255, 15) if not highlight else (255, 215, 0, 25)
        border_col = (255, 255, 255, 60) if not highlight else (255, 215, 0, 180)
        
        # Draw Box
        draw.rounded_rectangle([30, y, W-30, y+block_h], radius=20, fill=bg_col, outline=border_col, width=2)
        
        # Label (Top Center)
        lbl_size = int(block_h * 0.18)
        lbl_font = core.load_font(font_path, lbl_size)
        draw.text((W/2, y + block_h*0.2), label.upper(), font=lbl_font, fill="#AAAAAA", anchor="mm")
        
        # Value (Center, Large)
        val_size = int(block_h * 0.45)
        val_font = core.load_font(font_path, val_size)
        
        # Split Unit Logic (Number vs Unit)
        val_str = str(value)
        unit = ""
        if val_str.endswith(" Cr"): 
            val_str = val_str[:-3]
            unit = "Cr"
        elif val_str.endswith("%"):
            val_str = val_str[:-1]
            unit = "%"
            
        # Fit logic
        full_text = val_str + (" " + unit if unit else "")
        while val_font.getlength(full_text) > W * 0.8 and val_size > 20:
            val_size -= 5
            val_font = core.load_font(font_path, val_size)
            
        # Draw Main Number
        draw.text((W/2, y + block_h*0.6), full_text, font=val_font, fill=val_color, anchor="mm")
        
        # Sub-label (Bottom)
        if sub_label:
            sub_font = core.load_font(font_path, int(block_h * 0.15))
            draw.text((W/2, y + block_h*0.85), sub_label, font=sub_font, fill="#888888", anchor="mm")

    # Draw 3 Rows (Auto-spaced)
    _draw_glass_block(0, "Quarterly Revenue", f"{rev:,.0f} Cr", "Top Line")
    
    col = "#A5D6A7" if margin > 15 else "#FFF59D" if margin > 8 else "#EF9A9A" # Pastel
    _draw_glass_block(1, "Net Profit Margin", f"{margin:.1f}%", "Efficiency", val_color=col)
    
    status = "STRONG BUY" if margin > 15 else "HOLD" if margin > 8 else "WATCH"
    status_col = "#FFD700" if status == "STRONG BUY" else "white"
    _draw_glass_block(2, "Verdict", status, "Fundamental Signal", val_color=status_col, highlight=True)

    # 5. Footer (Compact)
    draw.rectangle([0, H-footer_h, W, H], fill=(0,0,0, 220))
    dot_x = W/2 - 120
    cy = H - (footer_h/2)
    
    # Pulse Dot
    draw.ellipse([dot_x, cy-10, dot_x+20, cy+10], fill="#F44336")
    draw.text((W/2, cy), "LIVE RESULTS ANALYSIS", font=core.load_font(font_path, int(footer_h*0.4)), fill="white", anchor="mm")

    img.save(out_path)
    return out_path

def render_rsi_thermometer(rsi_val, size, theme, out_path):
    """
    Visual: Pastel Soft-Glow RSI Gauge.
    """
    W, H = size
    img = Image.new("RGBA", size, (0,0,0,0))
    draw = ImageDraw.Draw(img)
    font_path = theme['font']
    
    bar_w, bar_h = W * 0.85, 70
    bx, by = (W - bar_w) / 2, H / 2
    
    # 1. Soft Pastel Gradient
    for i in range(int(bar_w)):
        ratio = i / bar_w
        if ratio < 0.5:
            # Pastel Red (#EF9A9A) -> Pastel Yellow (#FFF59D)
            r_ratio = ratio * 2
            r = int(239 + (255-239)*r_ratio)
            g = int(154 + (245-154)*r_ratio)
            b = int(154 + (157-154)*r_ratio)
        else:
            # Pastel Yellow (#FFF59D) -> Pastel Green (#A5D6A7)
            g_ratio = (ratio - 0.5) * 2
            r = int(255 + (165-255)*g_ratio)
            g = int(245 + (214-245)*g_ratio)
            b = int(157 + (167-157)*g_ratio)
        
        draw.line([(bx + i, by), (bx + i, by + bar_h)], fill=(r, g, b))

    # Rounded Border
    draw.rounded_rectangle([bx, by, bx+bar_w, by+bar_h], radius=15, outline="white", width=2)
    
    # 2. Labels (Subtle Grey)
    f_sm = core.load_font(font_path, 26)
    draw.text((bx, by + bar_h + 15), "OVERSOLD (Buy)", font=f_sm, fill="#EF9A9A", anchor="lt")
    draw.text((bx + bar_w, by + bar_h + 15), "OVERBOUGHT (Sell)", font=f_sm, fill="#A5D6A7", anchor="rt")
    
    # 3. Floating Badge Pointer
    px = bx + (rsi_val / 100 * bar_w)
    
    # Draw Triangle
    draw.polygon([(px, by - 5), (px - 15, by - 30), (px + 15, by - 30)], fill="white")
    
    # Draw Badge
    draw.rounded_rectangle([px - 50, by - 90, px + 50, by - 40], radius=15, fill="#263238", outline="white", width=2)
    
    # RSI Value
    draw.text((px, by - 65), f"{rsi_val:.1f}", font=core.load_font(font_path, 34), fill="white", anchor="mm")
    
    # "RSI" Label above badge
    draw.text((px, by - 110), "RSI", font=core.load_font(font_path, 22), fill="#FFD700", anchor="mm")

    img.save(out_path)
    return out_path

def render_railway_map(price_data, company_name, size, theme, out_path):
    """
    Visual: Railway Map (Fixed Title Overlap).
    """
    W, H = size
    img = Image.new("RGB", size, (20, 20, 25))
    draw = ImageDraw.Draw(img)
    font_path = theme['font']
    
    # Title Logic
    title = f"{company_name} EXP"
    t_size = 55
    t_font = core.load_font(font_path, t_size)
    # Aggressive shrink
    while t_font.getlength(title) > W * 0.9:
        t_size -= 5
        t_font = core.load_font(font_path, t_size)
    draw.text((W/2, 80), title, font=t_font, fill="#FFD700", anchor="mm")
    
    start = price_data.iloc[0]['Close']
    curr = price_data.iloc[-1]['Close']
    high = price_data['High'].max()
    low = price_data['Low'].min()
    
    points = [("START", start), ("LOW", low), ("HIGH", high), ("NOW", curr)]
    
    margin_y = 200
    avail_h = H - margin_y * 2
    min_p, max_p = low * 0.9, high * 1.1
    
    coords = []
    spacing = W / 5
    for i, (lbl, p) in enumerate(points):
        x = spacing * (i + 1)
        y = (H - margin_y) - ((p - min_p) / (max_p - min_p) * avail_h)
        coords.append((x, y, lbl, p))
        
    line_col = "#66BB6A" if curr > start else "#EF5350"
    
    # Smooth line
    draw.line([(c[0], c[1]) for c in coords], fill=line_col, width=10)
    
    for x, y, lbl, p in coords:
        draw.ellipse([x-15, y-15, x+15, y+15], fill="white", outline="black", width=2)
        draw.rounded_rectangle([x-50, y+25, x+50, y+75], radius=8, fill="#333333")
        draw.text((x, y+38), lbl, font=core.load_font(font_path, 18), fill="#AAAAAA", anchor="mm")
        draw.text((x, y+60), f"{p:,.0f}", font=core.load_font(font_path, 22), fill="white", anchor="mm")

    img.save(out_path)
    return out_path