import asyncio
from services.stock_service import get_stock_price
from services.mf_service import get_mf_nav

# Curated list of popular Indian & global stocks to scan each day
WATCHLIST_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "WIPRO.NS", "BAJFINANCE.NS", "AXISBANK.NS", "SBIN.NS", "LT.NS",
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META"
]

# Curated list of popular Indian Mutual Fund scheme codes to scan each day
WATCHLIST_MFS = [
    "120503",  # Mirae Asset Large Cap
    "119598",  # Axis Bluechip Fund
    "120716",  # SBI Small Cap Fund
    "118989",  # HDFC Mid-Cap Opportunities
    "119062",  # ICICI Pru Balanced Advantage
    "118701",  # Parag Parikh Flexi Cap
    "120175",  # Kotak Emerging Equity
]


async def get_top_performers() -> dict:
    """
    Fetches daily performance data for curated stocks and MFs,
    then returns the top 3 performers in each category.
    """
    stock_results = []
    mf_results = []

    # Fetch all stocks concurrently
    stock_tasks = [get_stock_price(ticker) for ticker in WATCHLIST_STOCKS]
    results = await asyncio.gather(*stock_tasks, return_exceptions=True)
    for ticker, result in zip(WATCHLIST_STOCKS, results):
        if isinstance(result, Exception):
            continue
        stock_results.append({
            "name": result.get("name", ticker),
            "ticker": ticker,
            "change_pct": result.get("change_pct", 0.0),
            "price": result.get("price", 0),
            "currency": result.get("currency", "INR")
        })

    # Fetch all MFs concurrently
    mf_tasks = [get_mf_nav(code) for code in WATCHLIST_MFS]
    mf_fetched = await asyncio.gather(*mf_tasks, return_exceptions=True)
    for result in mf_fetched:
        if isinstance(result, Exception):
            continue
        mf_results.append({
            "name": result.get("scheme_name", "Unknown Fund"),
            "change_pct": result.get("change_pct", 0.0),
            "nav": result.get("nav", 0)
        })

    # Sort and grab top 3 winners in each category
    top_stocks = sorted(stock_results, key=lambda x: x["change_pct"], reverse=True)[:3]
    top_mfs = sorted(mf_results, key=lambda x: x["change_pct"], reverse=True)[:3]

    return {"top_stocks": top_stocks, "top_mfs": top_mfs}
