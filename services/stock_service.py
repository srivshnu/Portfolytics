import asyncio
import time
import threading
import requests
import yfinance as yf

# ─────────────────────────────────────────────────────────────────────────────
# Yahoo Finance Session Manager
# ─────────────────────────────────────────────────────────────────────────────
class _YahooSession:
    """
    Manages a single Yahoo Finance HTTP session.

    Strategy:
    - Visit finance.yahoo.com at startup to get session cookies.
    - Fetch the crumb ONCE and store it.
    - Inject the crumb into every API call (chart / quote endpoints).
    - On 401, refresh cookies + crumb and retry ONCE.
    - Thread-safe refresh via a Lock.

    This bypasses yfinance's internal crumb logic entirely, preventing
    per-call crumb fetches that trigger Yahoo's 429 rate limiter.
    """
    _HOME  = "https://finance.yahoo.com"
    _CRUMB = "https://query1.finance.yahoo.com/v1/test/getcrumb"
    _CHART = "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
    _QUOTE = "https://query2.finance.yahoo.com/v7/finance/quote"

    _HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://finance.yahoo.com/',
    }

    def __init__(self):
        self._lock = threading.Lock()
        self.session = requests.Session()
        self.session.headers.update(self._HEADERS)
        self.crumb: str | None = None
        self._prime()

    def _prime(self):
        """Get Yahoo Finance cookies, then fetch the crumb."""
        try:
            self.session.get(self._HOME, timeout=15)
            time.sleep(1)                             # brief pause avoids back-to-back requests
            r = self.session.get(self._CRUMB, timeout=10)
            if r.status_code == 200 and r.text:
                self.crumb = r.text.strip()
                print("[YF] Session primed — crumb acquired.")
            else:
                print(f"[YF] Crumb fetch returned HTTP {r.status_code}; will retry on next 401.")
        except Exception as exc:
            print(f"[YF] Session prime warning: {exc}")

    def refresh_crumb(self):
        """Thread-safe crumb refresh — called automatically on 401 responses."""
        with self._lock:
            print("[YF] Refreshing crumb after 401 …")
            self._prime()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _params(self, extra: dict | None = None) -> dict:
        p = {'crumb': self.crumb} if self.crumb else {}
        if extra:
            p.update(extra)
        return p

    def _get(self, url: str, params: dict, retry: bool = True) -> requests.Response:
        r = self.session.get(url, params=params, timeout=15)
        if r.status_code == 401 and retry:
            self.refresh_crumb()
            if self.crumb:
                params['crumb'] = self.crumb
            r = self.session.get(url, params=params, timeout=15)
        return r

    # ── Public API ────────────────────────────────────────────────────────────

    def fetch_chart(self, symbol: str) -> dict:
        """GET /v8/finance/chart/{symbol} — returns the raw result[0] dict."""
        url = self._CHART.format(symbol=symbol)
        r = self._get(url, self._params({'interval': '1d', 'range': '2d'}))
        r.raise_for_status()
        result = r.json().get('chart', {}).get('result')
        if not result:
            err = r.json().get('chart', {}).get('error') or {}
            raise ValueError(f"No data for {symbol}: {err.get('description', 'unknown')}")
        return result[0]

    def fetch_quotes(self, symbols: list) -> list:
        """GET /v7/finance/quote — returns quote dicts for all symbols in ONE call."""
        r = self._get(self._QUOTE, self._params({
            'symbols': ','.join(symbols),
            'fields': (
                'regularMarketPrice,regularMarketPreviousClose,previousClose,'
                'regularMarketChange,regularMarketChangePercent,'
                'shortName,longName,currency'
            ),
        }))
        r.raise_for_status()
        return r.json().get('quoteResponse', {}).get('result', [])


# ─── Module-level session singleton ──────────────────────────────────────────
_yf = _YahooSession()

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
        result = _yf.fetch_chart(ticker)
        meta = result['meta']
        price = meta.get('regularMarketPrice')
        if price is None:
            raise ValueError(f"No price for {ticker}")
        prev = meta.get('regularMarketPreviousClose') or meta.get('previousClose') or price
        change = price - prev
        change_pct = (change / prev * 100) if prev else 0.0
        data = {
            'ticker': ticker,
            'name': meta.get('longName') or meta.get('shortName') or ticker,
            'price': price,
            'previous_close': prev,
            'change': change,
            'change_pct': change_pct,
            'currency': meta.get('currency', 'INR'),
        }
        _to_cache(ticker, data)
        return data

    try:
        return await asyncio.to_thread(_fetch)
    except Exception as e:
        raise ValueError(f"Error fetching {ticker}: {e}")


async def get_stock_prices_batch(tickers: list) -> dict:
    """
    Fetch prices for multiple tickers in a SINGLE /v7/finance/quote call.
    Serves cached results where available to minimise API load.
    """
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
        for q in _yf.fetch_quotes(missing):
            symbol = q.get('symbol')
            price = q.get('regularMarketPrice')
            if not symbol or not price:
                continue
            prev = q.get('regularMarketPreviousClose') or q.get('previousClose') or price
            change = q.get('regularMarketChange', price - prev)
            change_pct = q.get('regularMarketChangePercent', (change / prev * 100) if prev else 0.0)
            data = {
                'price': price,
                'previous_close': prev,
                'change': change,
                'change_pct': change_pct,
                'currency': q.get('currency', 'INR'),
            }
            _to_cache(symbol, data)
            batch[symbol] = data
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
            result = _yf.fetch_chart(ticker)
            meta = result['meta']
            if not meta.get('regularMarketPrice'):
                return None
            return {
                'ticker': ticker,
                'name': meta.get('longName') or meta.get('shortName') or ticker,
                'currency': meta.get('currency', 'INR'),
            }
        return await asyncio.to_thread(_fetch)
    except Exception:
        return None


async def get_stock_history(ticker: str, days: int = 7) -> list:
    def _fetch():
        t = yf.Ticker(ticker, session=_yf.session)
        hist = t.history(period=f'{days}d')
        return [
            {'date': d.strftime('%Y-%m-%d'), 'close': float(row['Close'])}
            for d, row in hist.iterrows()
        ]
    return await asyncio.to_thread(_fetch)


async def search_stock(query: str) -> list:
    try:
        def _fetch():
            s = yf.Search(query, max_results=10, enable_fuzzy_query=True, session=_yf.session)
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



