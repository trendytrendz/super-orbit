# ai_art_director/visuals/theme_config.py

THEMES = {
    "breaking_bar": {
        "description": "CNBC Style Red Banner",
        "overlay_asset": "breaking_bar/plate.png",
        "bg_mode": "full",
        "fonts": {"header": "Oswald-Bold.ttf", "body": "Montserrat-Bold.ttf"},
        "colors": {
            "header": "white", 
            "body": "black", 
            "accent": "#cc0000", 
            "ticker": "white"
        },
        "layout": {
            "logo": (150, 300),
            "ticker": (200, 880),  
            "header": (50, 950, 980),
            "body": (50, 1100, 980)
        },
        "effect": "shadow"
    },
    "market_dashboard": {
        "description": "Dark Financial Terminal",
        "overlay_asset": "market_dashboard/plate.png",
        "bg_mode": "top_half",
        "fonts": {"header": "Montserrat-Bold.ttf", "body": "Lato-Bold.ttf"},
        "colors": {"header": "black", "body": "#eeeeee", "accent": "#00ff00", "ticker": "#00ff00"},
        "layout": {
            "logo": (540, 750), 
            "ticker": (540, 910), 
            "header": (50, 970, 980), 
            "body": (80, 1150, 920)
        },
        "effect": "none"
    },
    "glass_stack": {
        "description": "TV Monitor Style (Gold)",
        "overlay_asset": "glass_stack/plate.png",
        "bg_mode": "blur",
        "fonts": {"header": "Oswald-Bold.ttf", "body": "Montserrat-Bold.ttf"},
        "colors": {
            "header": "white", 
            "body": "#ffcccc", 
            "accent": "white", 
            "ticker": "white"
        },
        "layout": {
            # --- FIX APPLIED HERE ---
            # Old: (340, 560) -> Too left and top-aligned
            # New: (540, 580) -> Perfectly centered in the red badge
            "ticker": (540, 580), 
            
            # Adjusted Logo slightly to center it better in the white strip
            "logo": (540, 715),   
            
            "header": (100, 950, 880),
            "body": (100, 1150, 880)
        },
        "effect": "shadow"
    },
    "neo_brutalist": {
        "description": "Gumroad Style",
        "overlay_asset": "neo_brutalist/plate.png",
        "bg_mode": "solid_random",
        "fonts": {"header": "BebasNeue-Regular.ttf", "body": "Montserrat-Bold.ttf"},
        "colors": {"header": "black", "body": "black", "accent": "black", "ticker": "white"},
        "layout": {"header": (120, 350, 840), "body": (120, 600, 840), "ticker": (120, 280)},
        "effect": "none"
    },
    "kinetic_typo": {
        "description": "TikTok Huge Text",
        "overlay_asset": "kinetic_typo/plate.png",
        "bg_mode": "darken",
        "fonts": {"header": "Oswald-Bold.ttf", "body": "Oswald-Bold.ttf"},
        "colors": {"header": "#FFFF00", "body": "white", "accent": "red", "ticker": "black"},
        "layout": {"header": (50, 300, 980), "body": (50, 800, 980), "ticker": (50, 250)},
        "effect": "outline"
    },
    "split_deck": {
        "description": "Split",
        "overlay_asset": "split_deck/plate.png",
        "bg_mode": "full",
        "fonts": {"header": "Montserrat-Bold.ttf", "body": "Lato-Bold.ttf"},
        "colors": {"header": "white", "body": "white", "accent": "black", "ticker": "yellow"},
        "layout": {"header": (50, 1000, 980), "body": (50, 1250, 980), "ticker": (50, 900)},
        "effect": "shadow"
    },
    "vertical_ticker": {
        "description": "Newspaper Pop-up Style",
        "overlay_asset": "vertical_ticker/plate.png",
        "bg_mode": "full",
        "fonts": {"header": "Oswald-Bold.ttf", "body": "Merriweather-Bold.ttf"},
        "colors": {
            "header": "white", 
            "body": "#1a1a1a", 
            "accent": "#cc0000", 
            "ticker": "#1a1a1a"
        },
        "layout": {
            "logo": (540, 400), 
            "ticker": (540, 560), 
            "header": (140, 680, 800), 
            "body": (140, 850, 800)
        },
        "effect": "none"
    }
}