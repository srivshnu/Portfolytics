import asyncio
import yfinance as yf
import httpx

async def get_stock_price(ticker: str) -> dict:
    def _fetch():
        try:
            t = yf.Ticker(ticker)
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
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = httpx.get(f'https://query2.finance.yahoo.com/v1/finance/search?q={query}', headers=headers, timeout=10)
            r.raise_for_status()
            return r.json().get('quotes', [])
        
        quotes = await asyncio.to_thread(_fetch)
        results = []
        for q in quotes:
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
    except Exception as e:
        print(f"Error searching stock {query}: {e}")
        return []
