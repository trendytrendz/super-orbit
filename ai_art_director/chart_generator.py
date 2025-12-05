# chart_generator.py
# v24.2.25 - Config-Driven Absolute Paths

import os
from . import chart_layouts
from . import config

def get_tmp_path(filename):
    # Safely join using Path object from config
    # This guarantees: /Users/.../lear_earn/outputs/tmp/images/filename
    return str(config.TMP_IMG_DIR / filename)

def make_sector_infographic(sector, market_cap, size, theme, out_png=None):
    path = out_png or get_tmp_path("sector_scale.png")
    return chart_layouts.draw_sector_infographic(sector, market_cap, size, theme, path)

def make_comparison_bar_chart(metric_name, data, size, theme, out_png=None):
    path = out_png or get_tmp_path("comparison.png")
    return chart_layouts.draw_comparison_bar_chart(metric_name, data, size, theme, path)

def make_stock_vs_stock_price_chart(dataframes, names, size, theme, out_png=None):
    path = out_png or get_tmp_path("stock_price_comp.png")
    return chart_layouts.draw_stock_vs_stock_price_chart(dataframes, names, size, theme, path)

def make_single_metric_chart(metric_name, metric_value, company_name, size, theme, out_png=None):
    path = out_png or get_tmp_path("single_metric.png")
    return chart_layouts.draw_single_metric_chart(metric_name, metric_value, company_name, size, theme, path)

def make_candlestick_chart(df, symbol, size, theme, out_png=None):
    path = out_png or get_tmp_path("price.png")
    return chart_layouts.draw_candlestick_chart(df, symbol, size, theme, path)

def make_index_comparison_chart(df_stock, df_index, stock_name, index_name, size, theme, out_png=None):
    path = out_png or get_tmp_path("index_comp.png")
    return chart_layouts.draw_index_comparison_chart(df_stock, df_index, stock_name, index_name, size, theme, path)

def make_shareholding_chart(data, size, theme, out_png=None):
    path = out_png or get_tmp_path("shareholding.png")
    return chart_layouts.draw_shareholding_chart(data, size, theme, path)

def make_financials_chart(y_symbol, size, theme, out_png=None):
    path = out_png or get_tmp_path("financials.png")
    return chart_layouts.draw_financials_chart(y_symbol, size, theme, path)

def make_peer_comparison_chart(peers_data, self_name, size, theme, out_png=None):
    path = out_png or get_tmp_path("peer_comp.png")
    return chart_layouts.draw_peer_comparison_chart(peers_data, self_name, size, theme, path)

def make_metrics_infographic(metrics, size, theme, out_png=None):
    path = out_png or get_tmp_path("metrics.png")
    return chart_layouts.draw_metrics_infographic(metrics, size, theme, path)