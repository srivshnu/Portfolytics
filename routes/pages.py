from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import get_current_user, require_auth, create_session, clear_session, hash_password, verify_password, set_flash, get_flash, clear_flash, RedirectToLogin
from database import get_db
from bson import ObjectId
from datetime import datetime, timezone
from services.stock_service import get_stock_price, validate_ticker, search_stock
from services.mf_service import get_mf_nav, search_mf
from services.gemini_service import analyze_asset

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def currency_fmt(value, currency_code="INR"):
    if value is None:
        return "N/A"
    symbols = {'USD': '$', 'INR': '₹', 'EUR': '€', 'GBP': '£', 'JPY': '¥'}
    sym = symbols.get(str(currency_code).upper(), f"{currency_code} ")
    try:
        return f"{sym}{float(value):.2f}"
    except (ValueError, TypeError):
        return f"{sym}{value}"

templates.env.filters["currency_fmt"] = currency_fmt

@router.get("/")
async def index(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/login", status_code=303)

@router.get("/login")
async def login_page(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    
    flash_message, flash_type = get_flash(request)
    response = templates.TemplateResponse(request, "login.html", {
        "user": user,
        "flash_message": flash_message,
        "flash_type": flash_type,
    })
    clear_flash(response)
    return response

@router.get("/register")
async def register_page(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    
    flash_message, flash_type = get_flash(request)
    response = templates.TemplateResponse(request, "register.html", {
        "user": user,
        "flash_message": flash_message,
        "flash_type": flash_type,
    })
    clear_flash(response)
    return response

@router.get("/dashboard")
async def dashboard(request: Request):
    user = await require_auth(request)
    flash_message, flash_type = get_flash(request)
    
    db = get_db()
    watchlist = await db.watchlists.find_one({"user_id": str(user["_id"])})
    
    stocks_data = []
    mf_data = []
    
    if watchlist:
        for stock in watchlist.get("stocks", []):
            try:
                price_data = await get_stock_price(stock["ticker"])
                if price_data:
                    stocks_data.append({
                        "ticker": stock["ticker"],
                        "name": stock["name"],
                        "price": price_data.get("price"),
                        "previous_close": price_data.get("previous_close"),
                        "change": price_data.get("change"),
                        "change_pct": price_data.get("change_pct"),
                        "currency": price_data.get("currency", "INR"),
                        "error": None
                    })
                else:
                    stocks_data.append({
                        "ticker": stock["ticker"],
                        "name": stock["name"],
                        "error": "Failed to fetch price"
                    })
            except Exception as e:
                stocks_data.append({
                    "ticker": stock["ticker"],
                    "name": stock["name"],
                    "error": str(e)
                })
                
        for mf in watchlist.get("mutual_funds", []):
            try:
                nav_data = await get_mf_nav(mf["scheme_code"])
                if nav_data:
                    mf_data.append({
                        "scheme_code": mf["scheme_code"],
                        "scheme_name": mf["scheme_name"],
                        "nav": nav_data.get("nav"),
                        "previous_nav": nav_data.get("previous_nav"),
                        "change": nav_data.get("change"),
                        "change_pct": nav_data.get("change_pct"),
                        "date": nav_data.get("date"),
                        "error": None
                    })
                else:
                    mf_data.append({
                        "scheme_code": mf["scheme_code"],
                        "scheme_name": mf["scheme_name"],
                        "error": "Failed to fetch NAV"
                    })
            except Exception as e:
                mf_data.append({
                    "scheme_code": mf["scheme_code"],
                    "scheme_name": mf["scheme_name"],
                    "error": str(e)
                })

    response = templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "flash_message": flash_message,
        "flash_type": flash_type,
        "stocks_data": stocks_data,
        "mf_data": mf_data
    })
    clear_flash(response)
    return response

@router.get("/add-stock")
async def add_stock_page(request: Request, q: str = ""):
    user = await require_auth(request)
    flash_message, flash_type = get_flash(request)
    
    results = []
    if q:
        results = await search_stock(q)
    
    response = templates.TemplateResponse(request, "add_stock.html", {
        "user": user,
        "flash_message": flash_message,
        "flash_type": flash_type,
        "query": q,
        "results": results
    })
    clear_flash(response)
    return response

@router.get("/add-mf")
async def add_mf_page(request: Request, q: str = ""):
    user = await require_auth(request)
    flash_message, flash_type = get_flash(request)
    
    results = []
    if q:
        results = await search_mf(q)
        
    response = templates.TemplateResponse(request, "add_mf.html", {
        "user": user,
        "flash_message": flash_message,
        "flash_type": flash_type,
        "query": q,
        "results": results
    })
    clear_flash(response)
    return response

@router.get("/asset/{asset_type}/{asset_id}")
async def asset_detail(request: Request, asset_type: str, asset_id: str):
    user = await require_auth(request)
    flash_message, flash_type = get_flash(request)
    
    db = get_db()
    asset = None
    ai_analysis = None
    error_message = None
    
    try:
        if asset_type == 'stock':
            price_data = await get_stock_price(asset_id)
            if price_data:
                asset = {
                    "asset_id": asset_id,
                    "asset_type": "stock",
                    "name": price_data.get("name", asset_id),
                    "current_price": price_data.get("price"),
                    "previous_price": price_data.get("previous_close"),
                    "change": price_data.get("change"),
                    "change_pct": price_data.get("change_pct"),
                    "currency": price_data.get("currency", "INR")
                }
            else:
                error_message = "Failed to fetch stock price."
        elif asset_type == 'mf':
            nav_data = await get_mf_nav(asset_id)
            if nav_data:
                asset = {
                    "asset_id": asset_id,
                    "asset_type": "mf",
                    "name": nav_data.get("scheme_name", asset_id),
                    "current_price": nav_data.get("nav"),
                    "previous_price": nav_data.get("previous_nav"),
                    "change": nav_data.get("change"),
                    "change_pct": nav_data.get("change_pct"),
                    "currency": "INR"
                }
            else:
                error_message = "Failed to fetch mutual fund NAV."
        else:
            error_message = "Invalid asset type."
            
        if asset:
            ai_analysis = await analyze_asset({
                "name": asset["name"],
                "asset_type": asset["asset_type"],
                "current_price": asset["current_price"],
                "previous_price": asset["previous_price"],
                "change_pct": asset["change_pct"],
                "is_alert": False
            })
    except Exception as e:
        error_message = str(e)

    # Get price history
    history = await db.price_history.find({"asset_id": asset_id, "asset_type": asset_type}).sort("recorded_at", -1).to_list(length=10)
    
    if error_message and not flash_message:
        flash_message = error_message
        flash_type = "error"

    response = templates.TemplateResponse(request, "asset_detail.html", {
        "user": user,
        "flash_message": flash_message,
        "flash_type": flash_type,
        "asset": asset,
        "ai_analysis": ai_analysis,
        "history": history
    })
    clear_flash(response)
    return response

@router.get("/settings")
async def settings_page(request: Request):
    user = await require_auth(request)
    flash_message, flash_type = get_flash(request)
    
    response = templates.TemplateResponse(request, "settings.html", {
        "user": user,
        "flash_message": flash_message,
        "flash_type": flash_type
    })
    clear_flash(response)
    return response
