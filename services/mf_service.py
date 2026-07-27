import httpx

async def get_mf_nav(scheme_code: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.mfapi.in/mf/{scheme_code}")
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch data for scheme {scheme_code}")
        
        data = response.json()
        if not data.get("data") or len(data["data"]) == 0:
            raise ValueError(f"No data available for scheme {scheme_code}")
        
        meta = data.get("meta", {})
        scheme_name = meta.get("scheme_name", scheme_code)
        
        latest_data = data["data"][0]
        nav = float(latest_data["nav"])
        date = latest_data["date"]
        
        previous_nav = nav
        if len(data["data"]) > 1:
            previous_nav = float(data["data"][1]["nav"])
            
        change = nav - previous_nav
        change_pct = (change / previous_nav * 100) if previous_nav else 0.0
        
        return {
            "scheme_code": scheme_code,
            "scheme_name": scheme_name,
            "nav": nav,
            "previous_nav": previous_nav,
            "change": change,
            "change_pct": change_pct,
            "date": date
        }

async def search_mf(query: str) -> list:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.mfapi.in/mf/search?q={query}")
            if response.status_code == 200:
                data = response.json()
                return [{"scheme_code": str(item["schemeCode"]), "scheme_name": item["schemeName"]} for item in data]
    except Exception:
        pass
    return []
