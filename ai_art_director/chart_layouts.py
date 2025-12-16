# chart_layouts.py
# v20.0.0

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

from . import config
from . import utils

CHART_TEXT_COLOR = "#FFFFFF"
TEXT_EFFECT = [path_effects.withStroke(linewidth=3, foreground='black')]

def draw_sector_infographic(sector, market_cap, size, theme, out_png):
    print(f"   -> Drawing sector & scale infographic...")
    if not sector and not market_cap: return None
    try:
        img = Image.new('RGBA', size, (0, 0, 0, 0)); draw = ImageDraw.Draw(img); font_path = theme['font']
        y_pos_sector, y_pos_mcap = size[1] * 0.35, size[1] * 0.65
        if sector:
            sector_font = utils.get_optimal_font_size(f"Sector: {sector}", 70, size[0] * 0.9, size[1] * 0.3, font_path)
            sector_text = f"Sector: {sector}"; sector_bbox = draw.textbbox((0, 0), sector_text, font=sector_font)
            draw.text(((size[0] - sector_bbox[2]) / 2, y_pos_sector), sector_text, font=sector_font, fill=theme['text'])
        if market_cap:
            # FIX (Phase 1): Corrected "₹" to "Rs." for consistency.
            mcap_text = f"Market Cap: Rs. {market_cap:,.0f} Cr"
            font_size = 100; mcap_font = ImageFont.truetype(font_path, font_size)
            # FIX (Phase 1): Robust font-shrinking loop.
            while draw.textlength(mcap_text, font=mcap_font) > size[0] * 0.95 and font_size > 20:
                font_size -= 4; mcap_font = ImageFont.truetype(font_path, font_size)
            mcap_bbox = draw.textbbox((0, 0), mcap_text, font=mcap_font)
            utils.draw_gradient_text(draw, mcap_text, mcap_font, ((size[0] - mcap_bbox[2]) / 2, y_pos_mcap), theme['accent'], theme.get('gradient_end', theme['accent']))
        img.save(out_png); return out_png
    except Exception as e: print(f"      - Could not draw Pillow sector infographic: {e}"); return None

def draw_comparison_bar_chart(metric_name, data, size, theme, out_png):
    print(f"   -> Drawing multi-stock comparison chart for: {metric_name}")
    names = list(data.keys()); values = list(data.values())
    if not names: return None
    plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
    fig.patch.set_alpha(0); ax.patch.set_alpha(0)
    colors = [theme['accent'], '#B0BEC5', '#FFCA28', '#8D6E63']; bar_colors = colors[:len(names)]
    plot_values = [v if v is not None else 0 for v in values]; bars = ax.bar(names, plot_values, color=bar_colors)
    for i, bar in enumerate(bars):
        yval = bar.get_height(); original_value = values[i]
        label_text = "N/A" if original_value is None else f"{original_value:,.0f}" if "Cr" in metric_name else f"{original_value:.1f}%" if "%" in metric_name else f"{original_value:.2f}"
        text_obj = ax.text(bar.get_x() + bar.get_width()/2.0, yval, label_text, va='bottom', ha='center', color=CHART_TEXT_COLOR, weight='bold', fontsize=14); text_obj.set_path_effects(TEXT_EFFECT)
    
    # ENHANCEMENT (Phase 1): More dynamic label rotation.
    num_names = len(names); avg_label_length = sum(len(name) for name in names) / num_names if num_names > 0 else 0
    if num_names > 5 or (num_names > 3 and avg_label_length > 8):
        ax.tick_params(axis='x', labelrotation=45, ha='right', labelsize=11)
    else:
        ax.tick_params(axis='x', labelrotation=0, labelsize=12)

    ax.set_ylabel(metric_name, color=CHART_TEXT_COLOR, path_effects=TEXT_EFFECT, fontsize=14); ax.set_title(f"Comparison: {metric_name}", color=CHART_TEXT_COLOR, fontsize=20, path_effects=TEXT_EFFECT); ax.tick_params(axis='y', colors=CHART_TEXT_COLOR, labelsize=12)
    for label in ax.get_xticklabels() + ax.get_yticklabels(): label.set_path_effects(TEXT_EFFECT)
    fig.tight_layout(pad=2.0); plt.savefig(out_png, transparent=True); plt.close(); return out_png

def draw_financials_chart(y_symbol, size, theme, out_png):
    try:
        financials = yf.Ticker(y_symbol).financials.T.head(4); financials['Net Income'] /= 1e7; financials['Total Revenue'] /= 1e7
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100); fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        bar_colors = [theme['accent'], '#B0BEC5']; financials[['Total Revenue', 'Net Income']].plot(kind='bar', ax=ax, color=bar_colors)

        # ENHANCEMENT (Phase 1): Dynamic label rotation for financials chart.
        num_labels = len(financials.index)
        if num_labels > 4: ax.tick_params(axis='x', labelrotation=30, ha='right')
        else: ax.tick_params(axis='x', labelrotation=0)

        ax.set_title("Financial Highlights (INR Crores)", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT); ax.tick_params(axis='y', colors=CHART_TEXT_COLOR)
        for label in ax.get_xticklabels() + ax.get_yticklabels(): label.set_path_effects(TEXT_EFFECT)
        legend = ax.legend(facecolor='none', edgecolor='none')
        for text in legend.get_texts(): text.set_color(CHART_TEXT_COLOR); text.set_path_effects(TEXT_EFFECT)
        fig.tight_layout(); plt.savefig(out_png, transparent=True); plt.close(); return out_png
    except Exception as e: print(f"      - Could not fetch financials chart: {e}"); return None

# ... (The rest of the chart functions are unchanged but included for completeness) ...

def draw_stock_vs_stock_price_chart(dataframes, names, size, theme, out_png):
    print("   -> Drawing multi-stock price comparison chart...")
    try:
        df_closes = {name: df['Close'] for name, df in zip(names, dataframes)}; df_merged = pd.concat(df_closes, axis=1).dropna(); df_norm = (df_merged / df_merged.iloc[0]) * 100
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100); fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        colors = [theme['accent'], '#FFFFFF', '#FFCA28', '#8D6E63']; linestyles = ['-', '--', ':', '-.']
        for i, name in enumerate(names):
            ax.plot(df_norm.index, df_norm[name], color=colors[i % len(colors)], label=name, linewidth=2.5 if i == 0 else 2.0, linestyle=linestyles[i % len(linestyles)])
        ax.set_title(f"Stock Performance Comparison (1-Year)", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT); ax.set_ylabel("Normalized Performance (%)", color=CHART_TEXT_COLOR, path_effects=TEXT_EFFECT); ax.tick_params(colors=CHART_TEXT_COLOR)
        for label in ax.get_xticklabels() + ax.get_yticklabels(): label.set_path_effects(TEXT_EFFECT)
        legend = ax.legend(facecolor='none', edgecolor='none'); [text.set_color(CHART_TEXT_COLOR) for text in legend.get_texts()]
        fig.tight_layout(pad=2.0); plt.savefig(out_png, transparent=True); plt.close(); return out_png
    except Exception as e: print(f"      - Could not draw multi-stock price chart: {e}"); return None

def draw_single_metric_chart(metric_name, metric_value, company_name, size, theme, out_png):
    print(f"   -> Drawing single metric chart for: {metric_name}"); plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
    fig.patch.set_alpha(0); ax.patch.set_alpha(0)
    val_str = f"{metric_value:,.2f}" if isinstance(metric_value, (int, float)) else str(metric_value); initial_font_size = 120
    if len(val_str) > 10: initial_font_size = 80
    font_path = theme['font']; optimal_font = utils.get_optimal_font_size(val_str, initial_font_size, size[0] * 0.9, size[1] * 0.4, font_path)
    text_obj = ax.text(0.5, 0.55, val_str, ha='center', va='center', fontsize=optimal_font.size, color=theme['accent'], weight='bold', transform=ax.transAxes); text_obj.set_path_effects(TEXT_EFFECT)
    sub_text_obj = ax.text(0.5, 0.35, metric_name, ha='center', va='center', fontsize=40, color=CHART_TEXT_COLOR, transform=ax.transAxes); sub_text_obj.set_path_effects(TEXT_EFFECT)
    title_obj = ax.text(0.5, 0.85, f"{company_name}\nValuation Snapshot", ha='center', va='center', fontsize=30, color=CHART_TEXT_COLOR, transform=ax.transAxes); title_obj.set_path_effects(TEXT_EFFECT)
    ax.axis('off'); plt.savefig(out_png, transparent=True, bbox_inches='tight', pad_inches=0.1); plt.close(); return out_png

def generate_color_palette(base_hex, n_colors=5):
    base_rgb = mcolors.to_rgb(base_hex); palette = [base_hex]
    for i in np.linspace(0.6, 0.2, n_colors - 1): light_color = [min(1, c + i) for c in base_rgb]; palette.append(mcolors.to_hex(light_color))
    return palette[:n_colors]

def draw_candlestick_chart(df, symbol, size, theme, out_png):
    try:
        # 1. Validation
        if df is None or df.empty:
            print("      - ⚠️ Chart Data Empty. Skipping.")
            return None
            
        # 2. Slice Data (Last 252 days / 1 year)
        df_chart = df.tail(252).copy()
        
        # 3. Calculate SMAs (Safety Check)
        # Only calc SMA200 if we have 200 data points in the FULL history, not just the slice
        # But here we assume df passed is already full history.
        
        ap = []
        
        # SMA 50
        if len(df) > 50:
            df_chart['SMA50'] = df['Close'].rolling(window=50).mean().tail(252)
            # Check if SMA50 has valid data in the visible range
            if not df_chart['SMA50'].dropna().empty:
                ap.append(mpf.make_addplot(df_chart['SMA50'], color='orange', width=1.5))

        # SMA 200
        if len(df) > 200:
            df_chart['SMA200'] = df['Close'].rolling(window=200).mean().tail(252)
            # Check if SMA200 has valid data in the visible range
            if not df_chart['SMA200'].dropna().empty:
                ap.append(mpf.make_addplot(df_chart['SMA200'], color='purple', width=1.5))

        # 4. Style
        mc = mpf.make_marketcolors(
            up=theme['accent'], down='#F44336', 
            edge={'up':theme['accent'], 'down':'#F44336'}, 
            wick={'up':theme['accent'], 'down':'#F44336'}, 
            volume=theme['accent'], ohlc='i'
        )
        
        grid_color = mcolors.to_hex(mcolors.to_rgba(CHART_TEXT_COLOR, alpha=0.15))
        s = mpf.make_mpf_style(marketcolors=mc, base_mpf_style='nightclouds', figcolor=config.BG_COLOR + '00', gridcolor=grid_color)
        
        # 5. Plot (Handle "Volume key error" if volume missing)
        kwargs = dict(
            type='candle', 
            style=s, 
            title=f"\n{symbol} Price Action", 
            ylabel='Price (INR)', 
            figsize=(size[0]/100, size[1]/100), 
            returnfig=True
        )
        
        if 'Volume' in df_chart.columns and not df_chart['Volume'].empty:
             kwargs['volume'] = True
             kwargs['ylabel_lower'] = 'Volume'

        if ap:
            kwargs['addplot'] = ap

        fig, axlist = mpf.plot(df_chart, **kwargs)
        
        # 6. Formatting (Text Color)
        for ax in axlist:
            ax.yaxis.label.set_color(CHART_TEXT_COLOR)
            ax.yaxis.label.set_path_effects(TEXT_EFFECT)
            ax.xaxis.label.set_color(CHART_TEXT_COLOR)
            ax.xaxis.label.set_path_effects(TEXT_EFFECT)
            for label in ax.get_xticklabels() + ax.get_yticklabels(): 
                label.set_color(CHART_TEXT_COLOR)
                label.set_path_effects(TEXT_EFFECT)
            ax.set_facecolor((0,0,0,0))
            
        axlist[0].title.set_color(CHART_TEXT_COLOR)
        axlist[0].title.set_path_effects(TEXT_EFFECT)
        
        fig.savefig(out_png, dpi=100, pad_inches=0.2, transparent=True)
        plt.close(fig)
        return out_png
        
    except Exception as e:
        print(f"      - ⚠️ Candlestick Chart Error: {e}")
        # import traceback; traceback.print_exc()
        return None

def draw_index_comparison_chart(df_stock, df_index, stock_name, index_name, size, theme, out_png):
    print("   -> Drawing index comparison chart...")
    try:
        df_merged = pd.concat([df_stock['Close'], df_index['Close']], axis=1, keys=[stock_name, index_name]).dropna(); df_norm = (df_merged / df_merged.iloc[0]) * 100
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100); fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        ax.plot(df_norm.index, df_norm[stock_name], color=theme['accent'], label=stock_name, linewidth=2.5, path_effects=TEXT_EFFECT)
        ax.plot(df_norm.index, df_norm[index_name], color=CHART_TEXT_COLOR, label=index_name, linewidth=1, linestyle='--')
        ax.set_title(f"{stock_name} vs. {index_name}", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT); ax.set_ylabel("Normalized Performance (%)", color=CHART_TEXT_COLOR, path_effects=TEXT_EFFECT); ax.tick_params(colors=CHART_TEXT_COLOR)
        for label in ax.get_xticklabels() + ax.get_yticklabels(): label.set_path_effects(TEXT_EFFECT)
        legend = ax.legend(facecolor='none', edgecolor='none'); [text.set_color(CHART_TEXT_COLOR) for text in legend.get_texts()]
        fig.tight_layout(); plt.savefig(out_png, transparent=True); plt.close(); return out_png
    except Exception as e: print(f"      - Could not draw index comparison chart: {e}"); return None

def draw_shareholding_chart(data, size, theme, out_png):
    print("   -> Drawing shareholding pattern chart..."); 
    try:
        labels = list(data.keys()); sizes = list(data.values()); color_palette = generate_color_palette(theme['accent'], n_colors=len(labels))
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100); fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        wedges, _, autotexts = ax.pie(sizes, autopct='%1.1f%%', startangle=90, colors=color_palette, wedgeprops=dict(width=0.4, edgecolor=config.BG_COLOR), pctdistance=0.8); plt.setp(autotexts, size=10, weight="bold", color=config.BG_COLOR)
        legend = ax.legend(wedges, labels, title="Shareholders", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), facecolor='none', edgecolor='none')
        for text in legend.get_texts(): text.set_color(CHART_TEXT_COLOR); text.set_path_effects(TEXT_EFFECT)
        legend.get_title().set_color(CHART_TEXT_COLOR); legend.get_title().set_path_effects(TEXT_EFFECT)
        ax.set_title("Shareholding Pattern", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT); plt.savefig(out_png, transparent=True, bbox_inches='tight'); plt.close(); return out_png
    except Exception as e: print(f"      - Could not draw shareholding chart: {e}"); return None

def draw_peer_comparison_chart(peers_data, self_name, size, theme, out_png):
    if not peers_data: return None
    print("   -> Drawing peer comparison chart..."); 
    try:
        names = list(peers_data.keys()); values = list(peers_data.values())
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100); fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        colors = ['#B0BEC5'] * len(names)
        if self_name in names: colors[names.index(self_name)] = theme['accent']
        bars = ax.barh(names, values, color=colors)
        ax.set_xlabel("P/E Ratio", color=CHART_TEXT_COLOR, path_effects=TEXT_EFFECT); ax.set_title("Peer Comparison (P/E Ratio)", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT); ax.tick_params(axis='x', colors=CHART_TEXT_COLOR); ax.tick_params(axis='y', colors=CHART_TEXT_COLOR)
        for label in ax.get_xticklabels() + ax.get_yticklabels(): label.set_path_effects(TEXT_EFFECT)
        fig.tight_layout(); plt.savefig(out_png, transparent=True); plt.close(); return out_png
    except Exception as e: print(f"      - Could not draw peer comparison chart: {e}"); return None

def draw_metrics_infographic(metrics, size, theme, out_png):
    print("   -> Drawing key metrics infographic (Pillow)..."); 
    try:
        img = Image.new('RGBA', size, (0, 0, 0, 0)); draw = ImageDraw.Draw(img); font_path = theme['font']
        title_text = "Key Metrics"; title_font = core.load_font(font_path, 60) 
        title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
        utils.draw_gradient_text(draw, title_text, title_font, ((size[0] - title_bbox[2]) / 2, size[1] * 0.1), theme['accent'], theme.get('gradient_end', theme['accent']))
        label_font = ImageFont.truetype(font_path, 36); y_start, y_step = size[1] * 0.3, 90
        left_column_x, right_column_x = size[0] * 0.15, size[0] * 0.85
        metrics_to_display = {k: v for k, v in metrics.items() if v is not None}
        for i, (key, value) in enumerate(metrics_to_display.items()):
            y_pos = y_start + (i * y_step); draw.text((left_column_x, y_pos), key, font=label_font, fill=CHART_TEXT_COLOR)
            value_text = f"{value:,.2f}" if isinstance(value, (int, float)) else str(value); initial_value_fontsize = 48 if len(value_text) < 12 else 36
            value_font = utils.get_optimal_font_size(value_text, initial_value_fontsize, size[0] * 0.4, y_step, font_path)
            value_bbox = draw.textbbox((0, 0), value_text, font=value_font)
            draw.text((right_column_x - value_bbox[2], y_pos), value_text, font=value_font, fill=theme['accent'])
        img.save(out_png); return out_png
    except Exception as e: print(f"      - Could not draw Pillow metrics infographic: {e}"); return None
