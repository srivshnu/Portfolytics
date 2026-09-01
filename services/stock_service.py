import asyncio
import requests
import yfinance as yf

# ------------------------------------------------------------------
# Shared persistent session — crumb is fetched once and reused
# across all yf.Ticker calls, preventing 429 rate-limits on the
# crumb endpoint that lead to cascading 401 errors.
# ------------------------------------------------------------------
_session = requests.Session()
_session.headers.update({
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
})

async def get_stock_price(ticker: str) -> dict:
    def _fetch():
        try:
            t = yf.Ticker(ticker, session=_session)
            info = t.info
            if not info:
                raise ValueError(f"Invalid ticker or no data: {ticker}")

            price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose')
            if price is None:
                raise ValueError(f"Could not extract price for {ticker}")

            # Use Yahoo's pre-computed change fields; fall back to manual calculation.
            # Guard against previousClose being present in the dict but set to None.
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

            return {
                "ticker": ticker,
                "name": name,
                "price": price,
                "previous_close": previous_close,
                "change": change,
                "change_pct": change_pct,
                "currency": info.get('currency', 'INR')
            }
        except Exception as e:
            raise ValueError(f"Error fetching data for {ticker}: {str(e)}")
    return await asyncio.to_thread(_fetch)

async def get_stock_prices_batch(tickers: list) -> dict:
    """
    Fetch prices for multiple tickers in a SINGLE yf.download() call.
    Used by the scheduler to avoid N separate crumb requests.
    Returns {ticker: {price, previous_close, change, change_pct, currency}}
    """
    if not tickers:
        return {}

    def _fetch():
        df = yf.download(
            tickers,
            period='2d',
            progress=False,
            auto_adjust=True,
            session=_session
        )
        results = {}
        if df.empty:
            return results

        multi = len(tickers) > 1
        try:
            close = df['Close'] if not multi else df['Close']
        except KeyError:
            return results

        for ticker in tickers:
            try:
                series = close[ticker] if multi else close
                series = series.dropna()
                if series.empty:
                    continue
                price = float(series.iloc[-1])
                prev = float(series.iloc[-2]) if len(series) >= 2 else price
                change = price - prev
                change_pct = (change / prev * 100) if prev else 0.0
                results[ticker] = {
                    'price': price,
                    'previous_close': prev,
                    'change': change,
                    'change_pct': change_pct,
                    'currency': 'INR'
                }
            except Exception as e:
                print(f"[batch] Error parsing {ticker}: {e}")
        return results

    try:
        return await asyncio.to_thread(_fetch)
    except Exception as e:
        print(f"[batch] yf.download failed: {e}")
        return {}


async def validate_ticker(ticker: str) -> dict | None:
    try:
        def _fetch():
            t = yf.Ticker(ticker, session=_session)
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
        t = yf.Ticker(ticker, session=_session)
        hist = t.history(period=f'{days}d')
        result = []
        for date, row in hist.iterrows():
            result.append({
                "date": date.strftime('%Y-%m-%d'),
                "close": row['Close']
            })
        return result
    return await asyncio.to_thread(_fetch)


async def search_stock(query: str) -> list:
    try:
        def _fetch():
            s = yf.Search(query, max_results=10, enable_fuzzy_query=True, session=_session)
            results = []
            for q in s.quotes:
                if q.get('quoteType') in ['EQUITY', 'ETF', 'MUTUALFUND']:
                    ticker = q.get('symbol')
                    name = q.get('shortname') or q.get('longname') or ticker
                    exchange = q.get('exchDisp', '')
                    if ticker:
                        results.append({
                            "ticker": ticker,
                            "name": name,
                            "exchange": exchange
                        })
            return results

        return await asyncio.to_thread(_fetch)
    except Exception as e:
        print(f"Error searching stock {query}: {e}")
        return []
