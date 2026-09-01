import asyncio
import time
import requests

# ─── 10-minute price cache ────────────────────────────────────────────────────
_cache: dict = {}        # ticker -> (price_dict, expires_at)
_CACHE_TTL = 600         # seconds

def _from_cache(ticker: str) -> dict | None:
    entry = _cache.get(ticker)
    return entry[0] if entry and time.time() < entry[1] else None

def _to_cache(ticker: str, data: dict):
    _cache[ticker] = (data, time.time() + _CACHE_TTL)

# ─── Raw Yahoo Finance API (No yfinance library!) ────────────────────────────
# We discovered that yfinance hangs for 10 minutes doing exponential backoffs 
# when query2 is IP-blocked. We can bypass this entirely by using query1 
# directly without crumbs.

def _fetch_yahoo_chart(ticker: str) -> dict:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    
    data = r.json()
    result = data.get('chart', {}).get('result')
    if not result:
        raise ValueError(f"No data returned for {ticker}")
        
    return result[0]['meta']

# ─────────────────────────────────────────────────────────────────────────────
# Public async functions
# ─────────────────────────────────────────────────────────────────────────────

async def get_stock_price(ticker: str) -> dict:
    if (cached := _from_cache(ticker)):
        return cached

    def _fetch():
        meta = _fetch_yahoo_chart(ticker)
        
        price = meta.get('regularMarketPrice')
        if price is None:
            raise ValueError(f"Could not extract price for {ticker}")

        previous_close = meta.get('previousClose') or meta.get('chartPreviousClose') or price
        change = price - previous_close
        change_pct = (change / previous_close * 100) if previous_close else 0.0

        name = meta.get('shortName') or meta.get('longName') or ticker

        data = {
            "ticker": ticker,
            "name": name,
            "price": price,
            "previous_close": previous_close,
            "change": change,
            "change_pct": change_pct,
            "currency": meta.get('currency', 'INR')
        }
        _to_cache(ticker, data)
        return data

    try:
        return await asyncio.to_thread(_fetch)
    except Exception as e:
        raise ValueError(f"Error fetching data for {ticker}: {str(e)}")

async def get_stock_prices_batch(tickers: list) -> dict:
    if not tickers:
        return {}

    results: dict = {}
    missing: list = []
    for t in tickers:
        cached = _from_cache(t)
        if cached:
            results[t] = cached
        else:
            missing.append(t)

    if not missing:
        return results

    def _fetch():
        batch = {}
        for t in missing:
            try:
                meta = _fetch_yahoo_chart(t)
                price = meta.get('regularMarketPrice')
                if not price:
                    continue
                    
                prev = meta.get('previousClose') or meta.get('chartPreviousClose') or price
                change = price - prev
                change_pct = (change / prev * 100) if prev else 0.0
                
                data = {
                    'price': price,
                    'previous_close': prev,
                    'change': change,
                    'change_pct': change_pct,
                    'currency': meta.get('currency', 'INR')
                }
                _to_cache(t, data)
                batch[t] = data
            except Exception as e:
                print(f"[batch] Error parsing {t}: {e}")
        return batch

    try:
        fresh = await asyncio.to_thread(_fetch)
        results.update(fresh)
    except Exception as exc:
        print(f"[batch] Quote fetch failed: {exc}")

    return results

async def validate_ticker(ticker: str) -> dict | None:
    try:
        def _fetch():
            meta = _fetch_yahoo_chart(ticker)
            if not meta.get('regularMarketPrice'):
                return None
            return {
                "ticker": ticker,
                "name": meta.get('shortName') or meta.get('longName') or ticker,
                "currency": meta.get('currency', 'INR')
            }
        return await asyncio.to_thread(_fetch)
    except Exception:
        return None

async def get_stock_history(ticker: str, days: int = 7) -> list:
    # History can still use query1 but we need historical data
    def _fetch():
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range={days}d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        
        result = r.json()['chart']['result'][0]
        timestamps = result.get('timestamp', [])
        close_prices = result.get('indicators', {}).get('quote', [{}])[0].get('close', [])
        
        from datetime import datetime
        history = []
        for ts, close in zip(timestamps, close_prices):
            if close is not None:
                history.append({
                    'date': datetime.fromtimestamp(ts).strftime('%Y-%m-%d'),
                    'close': float(close)
                })
        return history
    return await asyncio.to_thread(_fetch)

async def search_stock(query: str) -> list:
    try:
        def _fetch():
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=10"
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers, timeout=5)
            r.raise_for_status()
            
            quotes = r.json().get('quotes', [])
            return [
                {
                    'ticker': q.get('symbol'),
                    'name': q.get('shortname') or q.get('longname') or q.get('symbol'),
                    'exchange': q.get('exchDisp', ''),
                }
                for q in quotes
                if q.get('quoteType') in ['EQUITY', 'ETF', 'MUTUALFUND'] and q.get('symbol')
            ]
        return await asyncio.to_thread(_fetch)
    except Exception as exc:
        print(f"Error searching stock {query}: {exc}")
        return []



