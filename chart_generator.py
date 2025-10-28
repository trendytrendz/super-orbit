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

def make_sector_infographic(sector, market_cap, size, theme, out_png="outputs/tmp/sector_scale.png"):
    """Creates a Pillow infographic for Sector and Market Cap."""
    print(f"   -> Generating sector & scale infographic...")
    if not sector and not market_cap:
        return None
    try:
        img = Image.new('RGBA', size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        font_path = theme['font']
        if sector:
            sector_font = ImageFont.truetype(font_path, 70)
            sector_text = f"Sector: {sector}"
            sector_bbox = draw.textbbox((0, 0), sector_text, font=sector_font)
            sector_width = sector_bbox[2] - sector_bbox[0]
            sector_pos = ((size[0] - sector_width) / 2, size[1] * 0.3)
            draw.text((sector_pos[0] + 3, sector_pos[1] + 3), sector_text, font=sector_font, fill="#00000088")
            draw.text(sector_pos, sector_text, font=sector_font, fill=theme['text'])
        if market_cap:
            mcap_font = ImageFont.truetype(font_path, 90)
            mcap_text = f"Market Cap: ₹{market_cap:,.0f} Cr"
            mcap_bbox = draw.textbbox((0, 0), mcap_text, font=mcap_font)
            mcap_width = mcap_bbox[2] - mcap_bbox[0]
            mcap_pos = ((size[0] - mcap_width) / 2, size[1] * 0.6)
            draw.text((mcap_pos[0] + 3, mcap_pos[1] + 3), mcap_text, font=mcap_font, fill="#00000088")
            draw.text(mcap_pos, mcap_text, font=mcap_font, fill=theme['accent'])
        img.save(out_png)
        return out_png
    except Exception as e:
        print(f"      - Could not generate Pillow sector infographic: {e}")
        return None

def make_comparison_bar_chart(metric_name, data, size, theme, out_png="outputs/tmp/comparison.png"):
    print(f"   -> Generating multi-stock comparison chart for: {metric_name}")
    names = list(data.keys())
    values = list(data.values())
    if not names: return None
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
    fig.patch.set_alpha(0); ax.patch.set_alpha(0)
    colors = [theme['accent'], '#B0BEC5', '#FFCA28', '#8D6E63']
    bar_colors = colors[:len(names)]
    plot_values = [v if v is not None else 0 for v in values]
    bars = ax.bar(names, plot_values, color=bar_colors)
    for i, bar in enumerate(bars):
        yval = bar.get_height()
        original_value = values[i]
        if original_value is None: label_text = "N/A"
        elif "Cr" in metric_name: label_text = f"{original_value:,.0f}"
        elif "%" in metric_name: label_text = f"{original_value:.1f}%"
        else: label_text = f"{original_value:.2f}"
        text_obj = ax.text(bar.get_x() + bar.get_width()/2.0, yval, label_text, va='bottom', ha='center', color=CHART_TEXT_COLOR, weight='bold', fontsize=14)
        text_obj.set_path_effects(TEXT_EFFECT)
    ax.set_ylabel(metric_name, color=CHART_TEXT_COLOR, path_effects=TEXT_EFFECT, fontsize=14)
    ax.set_title(f"Comparison: {metric_name}", color=CHART_TEXT_COLOR, fontsize=20, path_effects=TEXT_EFFECT)
    ax.tick_params(axis='x', colors=CHART_TEXT_COLOR, labelsize=12)
    ax.tick_params(axis='y', colors=CHART_TEXT_COLOR, labelsize=12)
    for label in ax.get_xticklabels(): label.set_path_effects(TEXT_EFFECT)
    for label in ax.get_yticklabels(): label.set_path_effects(TEXT_EFFECT)
    fig.tight_layout(pad=2.0)
    plt.savefig(out_png, transparent=True)
    plt.close()
    return out_png

def make_stock_vs_stock_price_chart(dataframes, names, size, theme, out_png="outputs/tmp/stock_price_comp.png"):
    print("   -> Generating multi-stock price comparison chart...")
    try:
        df_closes = {name: df['Close'] for name, df in zip(names, dataframes)}
        df_merged = pd.concat(df_closes, axis=1).dropna()
        df_norm = (df_merged / df_merged.iloc[0]) * 100
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
        fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        colors = [theme['accent'], '#FFFFFF', '#FFCA28', '#8D6E63']
        linestyles = ['-', '--', ':', '-.']
        for i, name in enumerate(names):
            ax.plot(df_norm.index, df_norm[name], color=colors[i % len(colors)], label=name, linewidth=2.5 if i == 0 else 2.0, linestyle=linestyles[i % len(linestyles)])
        ax.set_title(f"Stock Performance Comparison (1-Year)", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT)
        ax.set_ylabel("Normalized Performance (%)", color=CHART_TEXT_COLOR, path_effects=TEXT_EFFECT)
        ax.tick_params(colors=CHART_TEXT_COLOR)
        for label in ax.get_xticklabels() + ax.get_yticklabels(): label.set_path_effects(TEXT_EFFECT)
        legend = ax.legend(facecolor='none', edgecolor='none')
        for text in legend.get_texts(): text.set_color(CHART_TEXT_COLOR); text.set_path_effects(TEXT_EFFECT)
        fig.tight_layout(pad=2.0); plt.savefig(out_png, transparent=True); plt.close()
        return out_png
    except Exception as e:
        print(f"      - Could not generate multi-stock price chart: {e}")
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
    # MODIFIED: Corrected the indentation error from the previous version.
    try:
        df_merged = pd.concat([df_stock['Close'], df_index['Close']], axis=1, keys=[stock_name, index_name]).dropna()
        df_norm = (df_merged / df_merged.iloc[0]) * 100
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
        fig.patch.set_alpha(0)
        ax.patch.set_alpha(0)
        ax.plot(df_norm.index, df_norm[stock_name], color=theme['accent'], label=stock_name, linewidth=2.5, path_effects=TEXT_EFFECT)
        ax.plot(df_norm.index, df_norm[index_name], color=CHART_TEXT_COLOR, label=index_name, linewidth=1, linestyle='--')
        ax.set_title(f"{stock_name} vs. {index_name}", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT)
        ax.set_ylabel("Normalized Performance (%)", color=CHART_TEXT_COLOR, path_effects=TEXT_EFFECT)
        ax.tick_params(colors=CHART_TEXT_COLOR)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_path_effects(TEXT_EFFECT)
        legend = ax.legend(facecolor='none', edgecolor='none')
        for text in legend.get_texts():
            text.set_color(CHART_TEXT_COLOR)
            text.set_path_effects(TEXT_EFFECT)
        fig.tight_layout()
        plt.savefig(out_png, transparent=True)
        plt.close()
        return out_png
    except Exception as e:
        print(f"      - Could not generate index comparison chart: {e}")
        return None

def make_shareholding_chart(data, size, theme, out_png="outputs/tmp/shareholding.png"):
    print("   -> Generating shareholding pattern chart...")
    try:
        labels = list(data.keys()); sizes = list(data.values()); color_palette = generate_color_palette(theme['accent'], n_colors=len(labels))
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100); fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        wedges, _, autotexts = ax.pie(sizes, autopct='%1.1f%%', startangle=90, colors=color_palette, wedgeprops=dict(width=0.4, edgecolor=config.BG_COLOR), pctdistance=0.8); plt.setp(autotexts, size=10, weight="bold", color=config.BG_COLOR)
        legend = ax.legend(wedges, labels, title="Shareholders", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), facecolor='none', edgecolor='none')
        for text in legend.get_texts(): text.set_color(CHART_TEXT_COLOR); text.set_path_effects(TEXT_EFFECT)
        legend.get_title().set_color(CHART_TEXT_COLOR); legend.get_title().set_path_effects(TEXT_EFFECT)
        ax.set_title("Shareholding Pattern", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT); plt.savefig(out_png, transparent=True, bbox_inches='tight'); plt.close(); return out_png
    except Exception as e: print(f"      - Could not generate shareholding chart: {e}"); return None

def make_financials_chart(y_symbol, size, theme, out_png="outputs/tmp/financials.png"):
    try:
        financials = yf.Ticker(y_symbol).financials.T.head(4); financials['Net Income'] /= 1e7; financials['Total Revenue'] /= 1e7
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100); fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        bar_colors = [theme['accent'], '#B0BEC5']; financials[['Total Revenue', 'Net Income']].plot(kind='bar', ax=ax, color=bar_colors)
        ax.set_title("Financial Highlights (INR Crores)", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT); ax.tick_params(axis='x', labelrotation=0, colors=CHART_TEXT_COLOR); ax.tick_params(axis='y', colors=CHART_TEXT_COLOR)
        for label in ax.get_xticklabels() + ax.get_yticklabels(): label.set_path_effects(TEXT_EFFECT)
        legend = ax.legend(facecolor='none', edgecolor='none')
        for text in legend.get_texts(): text.set_color(CHART_TEXT_COLOR); text.set_path_effects(TEXT_EFFECT)
        fig.tight_layout(); plt.savefig(out_png, transparent=True); plt.close(); return out_png
    except Exception as e: print(f"      - Could not fetch financials chart: {e}"); return None

def make_peer_comparison_chart(peers_data, self_name, size, theme, out_png="outputs/tmp/peer_comp.png"):
    if not peers_data: return None
    print("   -> Generating peer comparison chart...")
    try:
        names = list(peers_data.keys()); values = list(peers_data.values())
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100); fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        colors = ['#B0BEC5'] * len(names)
        if self_name in names: colors[names.index(self_name)] = theme['accent']
        bars = ax.barh(names, values, color=colors)
        ax.set_xlabel("P/E Ratio", color=CHART_TEXT_COLOR, path_effects=TEXT_EFFECT)
        ax.set_title("Peer Comparison (P/E Ratio)", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT)
        ax.tick_params(axis='x', colors=CHART_TEXT_COLOR); ax.tick_params(axis='y', colors=CHART_TEXT_COLOR)
        for label in ax.get_xticklabels() + ax.get_yticklabels(): label.set_path_effects(TEXT_EFFECT)
        fig.tight_layout(); plt.savefig(out_png, transparent=True); plt.close()
        return out_png
    except Exception as e: print(f"      - Could not generate peer comparison chart: {e}"); return None

def make_metrics_infographic(metrics, size, theme, out_png="outputs/tmp/metrics.png"):
    print("   -> Generating key metrics infographic (Pillow)...")
    try:
        img = Image.new('RGBA', size, (255, 255, 255, 0)); draw = ImageDraw.Draw(img); font_path = theme['font']; title_font = ImageFont.truetype(font_path, 60); title_text = "Key Metrics"; title_bbox = draw.textbbox((0, 0), title_text, font=title_font); title_width = title_bbox[2] - title_bbox[0]; title_pos = ((size[0] - title_width) / 2, size[1] * 0.1); draw.text((title_pos[0] + 3, title_pos[1] + 3), title_text, font=title_font, fill=(0,0,0,128)); draw.text(title_pos, title_text, font=title_font, fill=theme['accent']); label_font = ImageFont.truetype(font_path, 36); value_font = ImageFont.truetype(font_path, 42); y_start, y_step = size[1] * 0.3, 90; left_column_x, right_column_x = size[0] * 0.15, size[0] * 0.85
        metrics_to_display = {k: v for k, v in metrics.items() if v is not None}
        for i, (key, value) in enumerate(metrics_to_display.items()):
            y_pos = y_start + (i * y_step); label_text = key; label_pos = (left_column_x, y_pos); draw.text((label_pos[0] + 2, label_pos[1] + 2), label_text, font=label_font, fill=(0,0,0,100)); draw.text(label_pos, label_text, font=label_font, fill=CHART_TEXT_COLOR)
            value_text = f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)
            value_bbox = draw.textbbox((0, 0), value_text, font=value_font); value_width = value_bbox[2] - value_bbox[0]; value_pos = (right_column_x - value_width, y_pos); draw.text((value_pos[0] + 2, value_pos[1] + 2), value_text, font=value_font, fill=(0,0,0,100)); draw.text(value_pos, value_text, font=value_font, fill=theme['accent'])
        img.save(out_png); return out_png
    except Exception as e: print(f"      - Could not generate Pillow metrics infographic: {e}"); return None
