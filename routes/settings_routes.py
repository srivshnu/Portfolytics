from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from auth import require_auth, set_flash
from database import get_db
import re
import pytz
from services.scheduler_service import reschedule_user_report

router = APIRouter()

VALID_TIMEZONES = sorted(pytz.all_timezones)

@router.post("/update-schedule")
async def update_schedule(
    request: Request, 
    report_frequency: str = Form(...), 
    report_time: str = Form(...),
    timezone: str = Form("Asia/Kolkata")
):
    user = await require_auth(request)
    
    valid_frequencies = ['daily', 'every_12h', 'every_6h', 'weekly']
    if report_frequency not in valid_frequencies:
        response = RedirectResponse(url="/settings", status_code=303)
        set_flash(response, "Invalid frequency", "error")
        return response
        
    if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", report_time):
        response = RedirectResponse(url="/settings", status_code=303)
        set_flash(response, "Invalid time format. Use HH:MM", "error")
        return response

    if timezone not in pytz.all_timezones:
        response = RedirectResponse(url="/settings", status_code=303)
        set_flash(response, "Invalid timezone selected", "error")
        return response
        
    db = get_db()
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "settings.report_frequency": report_frequency,
            "settings.report_time": report_time,
            "settings.timezone": timezone
        }}
    )
    
    try:
        await reschedule_user_report(str(user["_id"]), report_frequency, report_time, timezone)
    except Exception as e:
        print(f"Failed to reschedule: {e}")
        
    response = RedirectResponse(url="/settings", status_code=303)
    set_flash(response, "Schedule updated successfully", "success")
    return response

@router.post("/update-alerts")
async def update_alerts(
    request: Request, 
    disaster_threshold_stock: float = Form(...), 
    disaster_threshold_mf: float = Form(...)
):
    user = await require_auth(request)
    
    if not (0 < disaster_threshold_stock <= 50) or not (0 < disaster_threshold_mf <= 50):
        response = RedirectResponse(url="/settings", status_code=303)
        set_flash(response, "Thresholds must be between 0 and 50", "error")
        return response
        
    db = get_db()
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "settings.disaster_threshold_stock": disaster_threshold_stock,
            "settings.disaster_threshold_mf": disaster_threshold_mf
        }}
    )
    
    response = RedirectResponse(url="/settings", status_code=303)
    set_flash(response, "Alert thresholds updated successfully", "success")
    return response
