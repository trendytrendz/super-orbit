# Refactored in v19.0.0
# This file is now a high-level orchestrator.
# The actual chart drawing logic is in chart_layouts.py

import os
import chart_layouts

def make_sector_infographic(sector, market_cap, size, theme, out_png="outputs/tmp/sector_scale.png"):
    return chart_layouts.draw_sector_infographic(sector, market_cap, size, theme, out_png)

def make_comparison_bar_chart(metric_name, data, size, theme, out_png="outputs/tmp/comparison.png"):
    return chart_layouts.draw_comparison_bar_chart(metric_name, data, size, theme, out_png)

def make_stock_vs_stock_price_chart(dataframes, names, size, theme, out_png="outputs/tmp/stock_price_comp.png"):
    return chart_layouts.draw_stock_vs_stock_price_chart(dataframes, names, size, theme, out_png)

def make_single_metric_chart(metric_name, metric_value, company_name, size, theme, out_png="outputs/tmp/single_metric.png"):
    return chart_layouts.draw_single_metric_chart(metric_name, metric_value, company_name, size, theme, out_png)

def make_candlestick_chart(df, symbol, size, theme, out_png="outputs/tmp/price.png"):
    return chart_layouts.draw_candlestick_chart(df, symbol, size, theme, out_png)

def make_index_comparison_chart(df_stock, df_index, stock_name, index_name, size, theme, out_png="outputs/tmp/index_comp.png"):
    return chart_layouts.draw_index_comparison_chart(df_stock, df_index, stock_name, index_name, size, theme, out_png)

def make_shareholding_chart(data, size, theme, out_png="outputs/tmp/shareholding.png"):
    return chart_layouts.draw_shareholding_chart(data, size, theme, out_png)

def make_financials_chart(y_symbol, size, theme, out_png="outputs/tmp/financials.png"):
    return chart_layouts.draw_financials_chart(y_symbol, size, theme, out_png)

def make_peer_comparison_chart(peers_data, self_name, size, theme, out_png="outputs/tmp/peer_comp.png"):
    return chart_layouts.draw_peer_comparison_chart(peers_data, self_name, size, theme, out_png)

def make_metrics_infographic(metrics, size, theme, out_png="outputs/tmp/metrics.png"):
    return chart_layouts.draw_metrics_infographic(metrics, size, theme, out_png)
