from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from auth import create_session, clear_session, hash_password, verify_password, set_flash
from database import get_db
from datetime import datetime, timezone

router = APIRouter()

@router.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    db = get_db()
    user = await db.users.find_one({"email": email})
    
    if not user or not verify_password(password, user.get("hashed_password", "")):
        response = RedirectResponse(url="/login", status_code=303)
        set_flash(response, "Invalid email or password", "error")
        return response
        
    response = RedirectResponse(url="/dashboard", status_code=303)
    create_session(response, str(user["_id"]))
    set_flash(response, "Welcome back!", "success")
    return response

@router.post("/register")
async def register(
    request: Request, 
    name: str = Form(...), 
    email: str = Form(...), 
    password: str = Form(...), 
    confirm_password: str = Form(...)
):
    if not name or not email or not password or not confirm_password:
        response = RedirectResponse(url="/register", status_code=303)
        set_flash(response, "All fields are required", "error")
        return response
        
    if password != confirm_password:
        response = RedirectResponse(url="/register", status_code=303)
        set_flash(response, "Passwords do not match", "error")
        return response
        
    db = get_db()
    if await db.users.find_one({"email": email}):
        response = RedirectResponse(url="/register", status_code=303)
        set_flash(response, "Email already registered", "error")
        return response
        
    hashed_pw = hash_password(password)
    
    new_user = {
        "name": name,
        "email": email,
        "hashed_password": hashed_pw,
        "created_at": datetime.now(timezone.utc),
        "settings": {
            "report_frequency": "daily",
            "report_time": "18:00",
            "timezone": "Asia/Kolkata",
            "disaster_threshold_stock": 5.0,
            "disaster_threshold_mf": 3.0
        }
    }
    
    result = await db.users.insert_one(new_user)
    
    # Create empty watchlist
    await db.watchlists.insert_one({
        "user_id": str(result.inserted_id),
        "stocks": [],
        "mutual_funds": []
    })
    
    response = RedirectResponse(url="/login", status_code=303)
    set_flash(response, "Account created! Please log in.", "success")
    return response

@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=303)
    clear_session(response)
    set_flash(response, "Logged out successfully", "success")
    return response
