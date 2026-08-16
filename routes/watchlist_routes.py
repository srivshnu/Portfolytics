from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from auth import require_auth, set_flash
from database import get_db
from datetime import datetime, timezone
from services.stock_service import validate_ticker
from services.mf_service import get_mf_nav, search_mf

router = APIRouter()

@router.post("/add-stock")
async def add_stock(request: Request, ticker: str = Form(...)):
    user = await require_auth(request)
    
    if not ticker or not ticker.strip():
        response = RedirectResponse(url="/add-stock", status_code=303)
        set_flash(response, "Ticker cannot be empty", "error")
        return response
        
    ticker = ticker.strip().upper()
    stock_info = await validate_ticker(ticker)
    
    if not stock_info:
        response = RedirectResponse(url=f"/add-stock?q={ticker}", status_code=303)
        set_flash(response, f"Ticker '{ticker}' not found. Did you mean one of these?", "error")
        return response
        
    db = get_db()
    watchlist = await db.watchlists.find_one({"user_id": str(user["_id"])})
    
    if watchlist:
        for s in watchlist.get("stocks", []):
            if s["ticker"] == ticker:
                response = RedirectResponse(url="/add-stock", status_code=303)
                set_flash(response, "Already tracking this stock", "error")
                return response
                
    await db.watchlists.update_one(
        {"user_id": str(user["_id"])},
        {"$push": {"stocks": {
            "ticker": ticker,
            "name": stock_info.get("name", ticker),
            "added_at": datetime.now(timezone.utc)
        }}},
        upsert=True
    )
    
    response = RedirectResponse(url="/dashboard", status_code=303)
    set_flash(response, f"Successfully added {ticker}", "success")
    return response

@router.post("/add-mf")
async def add_mf(request: Request, fund_input: str = Form(...)):
    """Handle both direct scheme code entry and name-based search (Did you mean?)."""
    user = await require_auth(request)

    fund_input = fund_input.strip()
    if not fund_input:
        response = RedirectResponse(url="/add-mf", status_code=303)
        set_flash(response, "Please enter a fund name or scheme code.", "error")
        return response

    # First: try treating the input as a direct scheme code
    if fund_input.isdigit():
        try:
            nav_data = await get_mf_nav(fund_input)
            if nav_data:
                # Valid code — proceed to add directly
                scheme_code = fund_input
                scheme_name = nav_data.get("scheme_name", fund_input)
                db = get_db()
                watchlist = await db.watchlists.find_one({"user_id": str(user["_id"])})
                if watchlist:
                    for mf in watchlist.get("mutual_funds", []):
                        if mf["scheme_code"] == scheme_code:
                            response = RedirectResponse(url="/add-mf", status_code=303)
                            set_flash(response, "Already tracking this mutual fund.", "error")
                            return response
                await db.watchlists.update_one(
                    {"user_id": str(user["_id"])},
                    {"$push": {"mutual_funds": {
                        "scheme_code": scheme_code,
                        "scheme_name": scheme_name,
                        "added_at": datetime.now(timezone.utc)
                    }}},
                    upsert=True
                )
                response = RedirectResponse(url="/dashboard", status_code=303)
                set_flash(response, f"Successfully added {scheme_name}.", "success")
                return response
        except Exception:
            pass  # Fall through to search

    # Second: treat input as a name — redirect to GET /add-mf?q=... for "Did you mean?"
    from urllib.parse import quote
    response = RedirectResponse(url=f"/add-mf?q={quote(fund_input)}", status_code=303)
    return response


@router.post("/add-mf-confirm")
async def add_mf_confirm(request: Request, scheme_code: str = Form(...), scheme_name: str = Form(...)):
    """Called when user clicks Add from the Did you mean? results."""
    user = await require_auth(request)

    if not scheme_code:
        response = RedirectResponse(url="/add-mf", status_code=303)
        set_flash(response, "Scheme code is required.", "error")
        return response

    db = get_db()
    watchlist = await db.watchlists.find_one({"user_id": str(user["_id"])})
    if watchlist:
        for mf in watchlist.get("mutual_funds", []):
            if mf["scheme_code"] == scheme_code:
                response = RedirectResponse(url="/add-mf", status_code=303)
                set_flash(response, "Already tracking this mutual fund.", "error")
                return response

    await db.watchlists.update_one(
        {"user_id": str(user["_id"])},
        {"$push": {"mutual_funds": {
            "scheme_code": scheme_code,
            "scheme_name": scheme_name,
            "added_at": datetime.now(timezone.utc)
        }}},
        upsert=True
    )

    response = RedirectResponse(url="/dashboard", status_code=303)
    set_flash(response, f"Successfully added {scheme_name}.", "success")
    return response

@router.post("/remove-asset")
async def remove_asset(request: Request, asset_type: str = Form(...), asset_id: str = Form(...)):
    user = await require_auth(request)
    db = get_db()
    
    if asset_type == 'stock':
        await db.watchlists.update_one(
            {"user_id": str(user["_id"])},
            {"$pull": {"stocks": {"ticker": asset_id}}}
        )
    elif asset_type == 'mf':
        await db.watchlists.update_one(
            {"user_id": str(user["_id"])},
            {"$pull": {"mutual_funds": {"scheme_code": asset_id}}}
        )
        
    response = RedirectResponse(url="/dashboard", status_code=303)
    set_flash(response, "Asset removed successfully", "success")
    return response
