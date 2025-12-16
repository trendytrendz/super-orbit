# ai_art_director/data_fetcher.py
# Refactored Facade v25.7.0

# 1. Stock Resolution
from .data.stock_resolver import resolve_symbol, update_nse_symbol_list as _update_nse

# 2. News Fetching & Logic
from .data.news_engine import (
    fetch_yfinance_news,
    fetch_google_news,
    fetch_moneycontrol_news,
    fetch_economic_times_news,
    rank_news_with_llm,
    score_news_relevance
)

# 3. Financial Data
from .data.financials import (
    fetch_tickertape_data,
    fetch_yfinance_supplemental_details,
    fetch_quarterly_financials,
    fetch_price_data,
    compute_price_snapshot
)

# 4. Assets
from .data.assets import fetch_company_logo

# Dry Run Verification:
# main.py calls data_fetcher.resolve_symbol -> maps to data.stock_resolver.resolve_symbol
# news_roundup_story calls data_fetcher.rank_news_with_llm -> maps to data.news_engine.rank_news_with_llm
print("✅ data_fetcher module loaded via Facade.")
