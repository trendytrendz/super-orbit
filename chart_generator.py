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

import config

# Define a high-contrast color and a path effect (outline) for all chart text
CHART_TEXT_COLOR = "#FFFFFF"
TEXT_EFFECT = [path_effects.withStroke(linewidth=3, foreground='black')]

def generate_color_palette(base_hex, n_colors=5):
    base_rgb = mcolors.to_rgb(base_hex)
    palette = [base_hex]
    for i in np.linspace(0.6, 0.2, n_colors - 1):
        light_color = [min(1, c + i) for c in base_rgb]
        palette.append(mcolors.to_hex(light_color))
    return palette[:n_colors]

def make_candlestick_chart(df, symbol, size, theme, out_png="outputs/tmp/price.png"):
    df_chart = df.tail(252).copy()
    df_chart['SMA50'] = df_chart['Close'].rolling(window=50).mean()
    df_chart['SMA200'] = df_chart['Close'].rolling(window=200).mean()
    mc = mpf.make_marketcolors(up=theme['accent'], down='#F44336', edge={'up':theme['accent'], 'down':'#F44336'},
                               wick={'up':theme['accent'], 'down':'#F44336'}, volume=theme['accent'], ohlc='i')
    grid_color = mcolors.to_hex(mcolors.to_rgba(CHART_TEXT_COLOR, alpha=0.15))
    s = mpf.make_mpf_style(marketcolors=mc, base_mpf_style='nightclouds',
                           figcolor=config.BG_COLOR + '00', gridcolor=grid_color)
    ap = [
        mpf.make_addplot(df_chart['SMA50'], color='orange', width=0.7),
        mpf.make_addplot(df_chart['SMA200'], color='purple', width=0.7),
    ]
    fig, axlist = mpf.plot(df_chart, type='candle', style=s, addplot=ap,
                           title=f"\n{symbol} Price Action",
                           ylabel='Price (INR)', volume=True, ylabel_lower='Volume',
                           figsize=(size[0]/100, size[1]/100), returnfig=True)
    
    for ax in axlist:
        ax.yaxis.label.set_color(CHART_TEXT_COLOR); ax.yaxis.label.set_path_effects(TEXT_EFFECT)
        ax.xaxis.label.set_color(CHART_TEXT_COLOR); ax.xaxis.label.set_path_effects(TEXT_EFFECT)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_color(CHART_TEXT_COLOR); label.set_path_effects(TEXT_EFFECT)
        ax.set_facecolor((0,0,0,0))
    axlist[0].title.set_color(CHART_TEXT_COLOR); axlist[0].title.set_path_effects(TEXT_EFFECT)
    
    fig.savefig(out_png, dpi=100, pad_inches=0.2, transparent=True)
    plt.close(fig)
    return out_png

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
        for text in legend.get_texts():
            text.set_color(CHART_TEXT_COLOR); text.set_path_effects(TEXT_EFFECT)
        
        fig.tight_layout(); plt.savefig(out_png, transparent=True); plt.close()
        return out_png
    except Exception as e:
        print(f"      - Could not generate index comparison chart: {e}")
        return None

def make_shareholding_chart(data, size, theme, out_png="outputs/tmp/shareholding.png"):
    print("   -> Generating shareholding pattern chart...")
    try:
        labels = list(data.keys()); sizes = list(data.values()); color_palette = generate_color_palette(theme['accent'], n_colors=len(labels))
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
        fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        
        wedges, _, autotexts = ax.pie(sizes, autopct='%1.1f%%', startangle=90, colors=color_palette,
                                          wedgeprops=dict(width=0.4, edgecolor=config.BG_COLOR), pctdistance=0.8)
        plt.setp(autotexts, size=10, weight="bold", color=config.BG_COLOR)
        
        legend = ax.legend(wedges, labels, title="Shareholders", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), facecolor='none', edgecolor='none')
        for text in legend.get_texts():
            text.set_color(CHART_TEXT_COLOR); text.set_path_effects(TEXT_EFFECT)
        legend.get_title().set_color(CHART_TEXT_COLOR); legend.get_title().set_path_effects(TEXT_EFFECT)
        ax.set_title("Shareholding Pattern", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT)
        
        plt.savefig(out_png, transparent=True, bbox_inches='tight'); plt.close()
        return out_png
    except Exception as e:
        print(f"      - Could not generate shareholding chart: {e}")
        return None

def make_financials_chart(y_symbol, size, theme, out_png="outputs/tmp/financials.png"):
    try:
        financials = yf.Ticker(y_symbol).financials.T.head(4); financials['Net Income'] /= 1e7; financials['Total Revenue'] /= 1e7
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
        fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        bar_colors = [theme['accent'], '#B0BEC5']
        financials[['Total Revenue', 'Net Income']].plot(kind='bar', ax=ax, color=bar_colors)
        
        ax.set_title("Financial Highlights (INR Crores)", color=CHART_TEXT_COLOR, fontsize=18, path_effects=TEXT_EFFECT)
        ax.tick_params(axis='x', labelrotation=0, colors=CHART_TEXT_COLOR)
        ax.tick_params(axis='y', colors=CHART_TEXT_COLOR)
        for label in ax.get_xticklabels() + ax.get_yticklabels(): label.set_path_effects(TEXT_EFFECT)
        legend = ax.legend(facecolor='none', edgecolor='none')
        for text in legend.get_texts():
            text.set_color(CHART_TEXT_COLOR); text.set_path_effects(TEXT_EFFECT)
        
        fig.tight_layout(); plt.savefig(out_png, transparent=True); plt.close()
        return out_png
    except Exception as e:
        print(f"      - Could not fetch financials chart: {e}")
        return None

def make_metrics_infographic(metrics, size, theme, out_png="outputs/tmp/metrics.png"):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
    fig.patch.set_alpha(0); ax.patch.set_alpha(0); ax.axis('off')

    title = ax.text(0.5, 0.9, "Key Metrics", color=theme['accent'], fontsize=36, 
                    weight='bold', ha='center', transform=ax.transAxes)
    title.set_path_effects(TEXT_EFFECT)

    metrics_list = list(metrics.items()); y_start = 0.75
    for i, (key, value) in enumerate(metrics_list):
        y_pos = y_start - i * 0.12
        key_text = ax.text(0.1, y_pos, key, color=theme['text'], alpha=0.9, 
                           fontsize=20, ha='left', va='center', transform=ax.transAxes)
        key_text.set_path_effects(TEXT_EFFECT)
        
        value_text = ax.text(0.9, y_pos, str(value), color=theme['accent'], 
                             fontsize=28, weight='bold', ha='right', va='center', 
                             transform=ax.transAxes)
        value_text.set_path_effects(TEXT_EFFECT)

    plt.savefig(out_png, transparent=True, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    return out_png
