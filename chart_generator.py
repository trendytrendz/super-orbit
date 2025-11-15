# chart_generator.py
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patheffects as path_effects
import mplfinance as mpf
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import config

CHART_TEXT_COLOR = "#FFFFFF"
TEXT_EFFECT = [path_effects.withStroke(linewidth=3, foreground='black')]

def make_metrics_infographic(metrics, size, theme, out_png="outputs/tmp/metrics.png"):
    print("   -> Generating key metrics infographic (Pillow)...")
    try:
        img = Image.new('RGBA', size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        font_path = theme['font']
        title_font = ImageFont.truetype(font_path, 60)
        title_text = "Key Metrics"
        title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_pos = ((size[0] - title_width) / 2, size[1] * 0.1)
        draw.text((title_pos[0] + 3, title_pos[1] + 3), title_text, font=title_font, fill=(0,0,0,128))
        draw.text(title_pos, title_text, font=title_font, fill=theme['accent'])
        label_font = ImageFont.truetype(font_path, 36)
        value_font = ImageFont.truetype(font_path, 42)
        y_start, y_step = size[1] * 0.3, 90
        left_column_x, right_column_x = size[0] * 0.15, size[0] * 0.85
        for i, (key, value) in enumerate(metrics.items()):
            y_pos = y_start + (i * y_step)
            label_text = key
            label_pos = (left_column_x, y_pos)
            draw.text((label_pos[0] + 2, label_pos[1] + 2), label_text, font=label_font, fill=(0,0,0,100))
            draw.text(label_pos, label_text, font=label_font, fill=CHART_TEXT_COLOR)
            value_text = str(value)
            value_bbox = draw.textbbox((0, 0), value_text, font=value_font)
            value_width = value_bbox[2] - value_bbox[0]
            value_pos = (right_column_x - value_width, y_pos)
            draw.text((value_pos[0] + 2, value_pos[1] + 2), value_text, font=value_font, fill=(0,0,0,100))
            draw.text(value_pos, value_text, font=value_font, fill=theme['accent'])
        img.save(out_png)
        return out_png
    except Exception as e:
        print(f"      - Could not generate Pillow metrics infographic: {e}")
        return None

def make_single_metric_chart(metric_name, metric_value, company_name, size, theme, out_png="outputs/tmp/single_metric.png"):
    print(f"   -> Generating single metric chart for: {metric_name}")
    plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
    fig.patch.set_alpha(0); ax.patch.set_alpha(0)
    val_str = str(metric_value) if metric_value else "N/A"
    text_obj = ax.text(0.5, 0.55, val_str, ha='center', va='center', fontsize=120, color=theme['accent'], weight='bold', transform=ax.transAxes); text_obj.set_path_effects(TEXT_EFFECT)
    sub_text_obj = ax.text(0.5, 0.35, metric_name, ha='center', va='center', fontsize=40, color=CHART_TEXT_COLOR, transform=ax.transAxes); sub_text_obj.set_path_effects(TEXT_EFFECT)
    title_obj = ax.text(0.5, 0.85, f"{company_name}\nValuation Snapshot", ha='center', va='center', fontsize=30, color=CHART_TEXT_COLOR, transform=ax.transAxes); title_obj.set_path_effects(TEXT_EFFECT)
    ax.axis('off'); plt.savefig(out_png, transparent=True, bbox_inches='tight', pad_inches=0.1); plt.close()
    return out_png

def make_peer_comparison_chart(peer_data, company_name, size, theme, out_png="outputs/tmp/peer_comp.png"):
    print("   -> Generating peer comparison chart...")
    try:
        tickers = list(peer_data.keys()); pe_ratios = list(peer_data.values())
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100); fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        bars = ax.barh(tickers, pe_ratios, color=theme['accent']); ax.invert_yaxis()
        for bar in bars:
            text_obj = ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, f'{bar.get_width():.2f}', va='center', ha='left', color=CHART_TEXT_COLOR, weight='bold')
            text_obj.set_path_effects(TEXT_EFFECT)
        ax.set_title(f"Peer Comparison (P/E Ratio)", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT); ax.tick_params(axis='y', colors=CHART_TEXT_COLOR); ax.tick_params(axis='x', colors=CHART_TEXT_COLOR)
        for label in ax.get_yticklabels(): label.set_path_effects(TEXT_EFFECT)
        fig.tight_layout(); plt.savefig(out_png, transparent=True); plt.close(); return out_png
    except Exception as e: print(f"      - Could not generate peer comparison chart: {e}"); return None

def make_comparison_bar_chart(metric_name, value_a, value_b, name_a, name_b, size, theme, out_png="outputs/tmp/comparison.png"):
    print(f"   -> Generating comparison chart for: {metric_name}")
    plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100); fig.patch.set_alpha(0); ax.patch.set_alpha(0)
    try: val_a_float = float(str(value_a).replace(",", "")) if value_a else 0; val_b_float = float(str(value_b).replace(",", "")) if value_b else 0
    except (ValueError, TypeError): val_a_float, val_b_float = 0, 0
    labels = [name_a, name_b]; values = [val_a_float, val_b_float]; colors = [theme['accent'], '#B0BEC5']; bars = ax.bar(labels, values, color=colors)
    for bar in bars:
        yval = bar.get_height(); label_text = f'{yval:,.2f}'
        text_obj = ax.text(bar.get_x() + bar.get_width()/2.0, yval, label_text, va='bottom', ha='center', color=CHART_TEXT_COLOR, weight='bold'); text_obj.set_path_effects(TEXT_EFFECT)
    ax.set_ylabel(metric_name, color=CHART_TEXT_COLOR, path_effects=TEXT_EFFECT); ax.set_title(f"Comparison: {metric_name}", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT); ax.tick_params(axis='x', colors=CHART_TEXT_COLOR); ax.tick_params(axis='y', colors=CHART_TEXT_COLOR)
    for label in ax.get_xticklabels(): label.set_path_effects(TEXT_EFFECT)
    for label in ax.get_yticklabels(): label.set_path_effects(TEXT_EFFECT)
    fig.tight_layout(); plt.savefig(out_png, transparent=True); plt.close(); return out_png

def make_stock_vs_stock_price_chart(df_a, df_b, name_a, name_b, size, theme, out_png="outputs/tmp/stock_price_comp.png"):
    print("   -> Generating stock vs. stock price comparison chart...")
    try:
        df_merged = pd.concat([df_a['Close'], df_b['Close']], axis=1, keys=[name_a, name_b]).dropna(); df_norm = (df_merged / df_merged.iloc[0]) * 100
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100); fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        ax.plot(df_norm.index, df_norm[name_a], color=theme['accent'], label=name_a, linewidth=2.5, path_effects=TEXT_EFFECT); ax.plot(df_norm.index, df_norm[name_b], color=CHART_TEXT_COLOR, label=name_b, linewidth=1.5, linestyle='--')
        ax.set_title(f"{name_a} vs. {name_b} (1-Year Performance)", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT); ax.set_ylabel("Normalized Performance (%)", color=CHART_TEXT_COLOR, path_effects=TEXT_EFFECT); ax.tick_params(colors=CHART_TEXT_COLOR)
        for label in ax.get_xticklabels() + ax.get_yticklabels(): label.set_path_effects(TEXT_EFFECT)
        legend = ax.legend(facecolor='none', edgecolor='none')
        for text in legend.get_texts(): text.set_color(CHART_TEXT_COLOR); text.set_path_effects(TEXT_EFFECT)
        fig.tight_layout(); plt.savefig(out_png, transparent=True); plt.close(); return out_png
    except Exception as e: print(f"      - Could not generate stock vs stock price chart: {e}"); return None

def generate_color_palette(base_hex, n_colors=5):
    base_rgb = mcolors.to_rgb(base_hex); palette = [base_hex]
    for i in np.linspace(0.6, 0.2, n_colors - 1): light_color = [min(1, c + i) for c in base_rgb]; palette.append(mcolors.to_hex(light_color))
    return palette[:n_colors]

def make_candlestick_chart(df, symbol, size, theme, out_png="outputs/tmp/price.png"):
    df_chart = df.tail(252).copy(); df_chart['SMA50'] = df_chart['Close'].rolling(window=50).mean(); df_chart['SMA200'] = df_chart['Close'].rolling(window=200).mean()
    mc = mpf.make_marketcolors(up=theme['accent'], down='#F44336', edge={'up':theme['accent'], 'down':'#F44336'}, wick={'up':theme['accent'], 'down':'#F44336'}, volume=theme['accent'], ohlc='i')
    grid_color = mcolors.to_hex(mcolors.to_rgba(CHART_TEXT_COLOR, alpha=0.15)); s = mpf.make_mpf_style(marketcolors=mc, base_mpf_style='nightclouds', figcolor=config.BG_COLOR + '00', gridcolor=grid_color)
    ap = [mpf.make_addplot(df_chart['SMA50'], color='orange', width=0.7), mpf.make_addplot(df_chart['SMA200'], color='purple', width=0.7)]
    fig, axlist = mpf.plot(df_chart, type='candle', style=s, addplot=ap, title=f"\n{symbol} Price Action", ylabel='Price (INR)', volume=True, ylabel_lower='Volume', figsize=(size[0]/100, size[1]/100), returnfig=True)
    for ax in axlist:
        ax.yaxis.label.set_color(CHART_TEXT_COLOR); ax.yaxis.label.set_path_effects(TEXT_EFFECT); ax.xaxis.label.set_color(CHART_TEXT_COLOR); ax.xaxis.label.set_path_effects(TEXT_EFFECT)
        for label in ax.get_xticklabels() + ax.get_yticklabels(): label.set_color(CHART_TEXT_COLOR); label.set_path_effects(TEXT_EFFECT)
        ax.set_facecolor((0,0,0,0))
    axlist[0].title.set_color(CHART_TEXT_COLOR); axlist[0].title.set_path_effects(TEXT_EFFECT)
    fig.savefig(out_png, dpi=100, pad_inches=0.2, transparent=True); plt.close(fig); return out_png

def make_index_comparison_chart(df_stock, df_index, stock_name, index_name, size, theme, out_png="outputs/tmp/index_comp.png"):
    print("   -> Generating index comparison chart...")
    try:
        df_merged = pd.concat([df_stock['Close'], df_index['Close']], axis=1, keys=[stock_name, index_name]).dropna()
        df_norm = (df_merged / df_merged.iloc[0]) * 100
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
        fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        ax.plot(df_norm.index, df_norm[stock_name], color=theme['accent'], label=stock_name, linewidth=2.5, path_effects=TEXT_EFFECT)
        ax.plot(df_norm.index, df_norm[index_name], color=CHART_TEXT_COLOR, label=index_name, linewidth=1, linestyle='--')
        ax.set_title(f"{stock_name} vs. {index_name}", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT)
        ax.set_ylabel("Normalized Performance (%)", color=CHART_TEXT_COLOR, path_effects=TEXT_EFFECT)
        ax.tick_params(colors=CHART_TEXT_COLOR)
        for label in ax.get_xticklabels() + ax.get_yticklabels(): label.set_path_effects(TEXT_EFFECT)
        legend = ax.legend(facecolor='none', edgecolor='none')
        for text in legend.get_texts(): text.set_color(CHART_TEXT_COLOR); text.set_path_effects(TEXT_EFFECT)
        fig.tight_layout(); plt.savefig(out_png, transparent=True); plt.close()
        return out_png
    except Exception as e:
        print(f"      - Could not generate index comparison chart: {e}")
        return None

def make_shareholding_chart(data, size, theme, out_png="outputs/tmp/shareholding.png"):
    print("   -> Generating shareholding pattern chart...")
    try:
        labels = list(data.keys()); sizes = list(data.values())
        color_palette = generate_color_palette(theme['accent'], n_colors=len(labels))
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
        fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        wedges, _, autotexts = ax.pie(sizes, autopct='%1.1f%%', startangle=90, colors=color_palette, wedgeprops=dict(width=0.4, edgecolor=config.BG_COLOR), pctdistance=0.8)
        plt.setp(autotexts, size=10, weight="bold", color=config.BG_COLOR)
        legend = ax.legend(wedges, labels, title="Shareholders", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), facecolor='none', edgecolor='none')
        for text in legend.get_texts(): text.set_color(CHART_TEXT_COLOR); text.set_path_effects(TEXT_EFFECT)
        legend.get_title().set_color(CHART_TEXT_COLOR); legend.get_title().set_path_effects(TEXT_EFFECT)
        ax.set_title("Shareholding Pattern", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT)
        plt.savefig(out_png, transparent=True, bbox_inches='tight'); plt.close()
        return out_png
    except Exception as e:
        print(f"      - Could not generate shareholding chart: {e}")
        return None

def make_financials_chart(y_symbol, size, theme, out_png="outputs/tmp/financials.png"):
    try:
        financials = yf.Ticker(y_symbol).financials.T.head(4)
        financials['Net Income'] /= 1e7; financials['Total Revenue'] /= 1e7
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
        fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        bar_colors = [theme['accent'], '#B0BEC5']
        financials[['Total Revenue', 'Net Income']].plot(kind='bar', ax=ax, color=bar_colors)
        ax.set_title("Financial Highlights (INR Crores)", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT)
        ax.tick_params(axis='x', labelrotation=0, colors=CHART_TEXT_COLOR)
        ax.tick_params(axis='y', colors=CHART_TEXT_COLOR)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_path_effects(TEXT_EFFECT)
        legend = ax.legend(facecolor='none', edgecolor='none')
        for text in legend.get_texts():
            text.set_color(CHART_TEXT_COLOR); text.set_path_effects(TEXT_EFFECT)
        fig.tight_layout(); plt.savefig(out_png, transparent=True); plt.close()
        return out_png
    except Exception as e:
        print(f"      - Could not fetch financials chart: {e}")
        return None
