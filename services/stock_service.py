import asyncio
import time
import yfinance as yf

# ─── 10-minute price cache ────────────────────────────────────────────────────
# Prevents the dashboard and scheduler from hitting Yahoo repeatedly for the
# same ticker within the same polling window.
_cache: dict = {}        # ticker -> (price_dict, expires_at)
_CACHE_TTL = 600         # seconds

def _from_cache(ticker: str) -> dict | None:
    entry = _cache.get(ticker)
    return entry[0] if entry and time.time() < entry[1] else None

def _to_cache(ticker: str, data: dict):
    _cache[ticker] = (data, time.time() + _CACHE_TTL)

# ─────────────────────────────────────────────────────────────────────────────
# Public async functions
# ─────────────────────────────────────────────────────────────────────────────

async def get_stock_price(ticker: str) -> dict:
    if (cached := _from_cache(ticker)):
        return cached

    def _fetch():
        t = yf.Ticker(ticker)
        info = t.info
        if not info:
            raise ValueError(f"Invalid ticker or no data: {ticker}")

        price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose')
        if price is None:
            raise ValueError(f"Could not extract price for {ticker}")

        change = info.get('regularMarketChange')
        change_pct = info.get('regularMarketChangePercent')

        previous_close = (
            info.get('regularMarketPreviousClose')
            or info.get('previousClose')
        )

        if change is None or change_pct is None:
            if previous_close:
                change = price - previous_close
                change_pct = (change / previous_close * 100)
            else:
                change = 0.0
                change_pct = 0.0

        previous_close = previous_close or price
        name = info.get('shortName') or info.get('longName') or ticker

        data = {
            "ticker": ticker,
            "name": name,
            "price": price,
            "previous_close": previous_close,
            "change": change,
            "change_pct": change_pct,
            "currency": info.get('currency', 'INR')
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
        df = yf.download(missing, period='2d', progress=False, auto_adjust=True)
        batch = {}
        if df.empty:
            return batch

        multi = len(missing) > 1
        try:
            close = df['Close'] if not multi else df['Close']
        except KeyError:
            return batch

        # In yf.download, currency is not returned. We will fetch info for each missing to cache properly,
        # or we just rely on Ticker(t).info to get accurate currencies for the batch.
        # Since downloading batch info doesn't exist cleanly in yfinance without loop, we'll just loop Ticker().
        # yf.download was causing the missing currency bug! Let's just use Ticker.info in a loop
        # since yf's internal requests handle rate limits better now.
        for t in missing:
            try:
                tk = yf.Ticker(t)
                info = tk.info
                if not info:
                    continue
                price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose')
                if not price:
                    continue
                prev = info.get('regularMarketPreviousClose') or info.get('previousClose') or price
                change = info.get('regularMarketChange')
                change_pct = info.get('regularMarketChangePercent')
                if change is None or change_pct is None:
                    change = price - prev
                    change_pct = (change / prev * 100) if prev else 0.0
                
                data = {
                    'price': price,
                    'previous_close': prev,
                    'change': change,
                    'change_pct': change_pct,
                    'currency': info.get('currency', 'INR')
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
            t = yf.Ticker(ticker)
            return t.info
        info = await asyncio.to_thread(_fetch)
        if not info or ('shortName' not in info and 'longName' not in info and 'regularMarketPrice' not in info):
            return None
        return {
            "ticker": ticker,
            "name": info.get('shortName') or info.get('longName') or ticker,
            "currency": info.get('currency', 'INR')
        }
    except Exception:
        return None

async def get_stock_history(ticker: str, days: int = 7) -> list:
    def _fetch():
        t = yf.Ticker(ticker)
        hist = t.history(period=f'{days}d')
        return [
            {'date': d.strftime('%Y-%m-%d'), 'close': float(row['Close'])}
            for d, row in hist.iterrows()
        ]
    return await asyncio.to_thread(_fetch)

async def search_stock(query: str) -> list:
    try:
        def _fetch():
            # Keep search fuzzy via raw yfinance logic
            import requests
            s = yf.Search(query, max_results=10, enable_fuzzy_query=True)
            return [
                {
                    'ticker': q.get('symbol'),
                    'name': q.get('shortname') or q.get('longname') or q.get('symbol'),
                    'exchange': q.get('exchDisp', ''),
                }
                for q in s.quotes
                if q.get('quoteType') in ['EQUITY', 'ETF', 'MUTUALFUND'] and q.get('symbol')
            ]
        return await asyncio.to_thread(_fetch)
    except Exception as exc:
        print(f"Error searching stock {query}: {exc}")
        return []



