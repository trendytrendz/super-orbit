THEMES = {
    "breaking_bar": {
        "description": "CNBC Style Red Banner",
        "overlay_asset": "breaking_bar/plate.png",
        "bg_mode": "full",
        "fonts": {"header": "Oswald-Bold.ttf", "body": "Montserrat-Bold.ttf"},
        "colors": {"header": "white", "body": "black", "accent": "#cc0000", "ticker": "white"},
        "layout": {
            # MOVED UP BY 200px
            "header": (50, 950, 980),  # Was 1150
            "body": (50, 1100, 980),   # Was 1300
            "ticker": (60, 860)        # Was 1060
        },
        "effect": "shadow"
    },
    # ... (Keep other themes exactly as they were)
    "market_dashboard": {
        "description": "Dark Financial Terminal",
        "overlay_asset": "market_dashboard/plate.png",
        "bg_mode": "top_half",
        "fonts": {"header": "Montserrat-Bold.ttf", "body": "Lato-Bold.ttf"},
        "colors": {"header": "black", "body": "#eeeeee", "accent": "#00ff00", "ticker": "#00ff00"},
        "layout": {"header": (50, 970, 980), "body": (80, 1150, 920), "ticker": (50, 910)},
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
    "neo_brutalist": {
        "description": "Gumroad Style",
        "overlay_asset": "neo_brutalist/plate.png",
        "bg_mode": "solid_random",
        "fonts": {"header": "BebasNeue-Regular.ttf", "body": "Montserrat-Bold.ttf"},
        "colors": {"header": "black", "body": "black", "accent": "black", "ticker": "white"},
        "layout": {"header": (120, 350, 840), "body": (120, 600, 840), "ticker": (120, 280)},
        "effect": "none"
    },
    "glass_stack": {
        "description": "Apple Vision",
        "overlay_asset": "glass_stack/plate.png",
        "bg_mode": "blur",
        "fonts": {"header": "Montserrat-Bold.ttf", "body": "Montserrat-Regular.ttf"},
        "colors": {"header": "white", "body": "#eeeeee", "accent": "white", "ticker": "white"},
        "layout": {"header": (100, 350, 880), "body": (100, 550, 880), "ticker": (100, 250)},
        "effect": "shadow"
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
        "description": "PIP Frame",
        "overlay_asset": "vertical_ticker/plate.png",
        "bg_mode": "pip",
        "fonts": {"header": "Lato-Bold.ttf", "body": "Montserrat-Regular.ttf"},
        "colors": {"header": "white", "body": "#cccccc", "accent": "#0055ff", "ticker": "white"},
        "layout": {"header": (50, 1200, 980), "body": (50, 1350, 980), "ticker": (50, 1150)},
        "effect": "none"
    }
}