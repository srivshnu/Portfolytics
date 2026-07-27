import asyncio
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import settings
from database import get_db
from services.stock_service import get_stock_price
from services.mf_service import get_mf_nav
from services.gemini_service import analyze_asset, generate_portfolio_report
from services.mail_service import send_email, build_report_html, build_alert_html

scheduler = None

async def disaster_monitor():
    try:
        db = get_db()
        watchlists = await db.watchlists.find().to_list(length=None)
        
        # Aggregate unique assets
        stocks = set()
        mfs = set()
        
        for w in watchlists:
            for s in w.get('stocks', []):
                stocks.add(s['ticker'])
            for m in w.get('mutual_funds', []):
                mfs.add(m['scheme_code'])
                
        asset_updates = []
        
        for ticker in stocks:
            try:
                data = await get_stock_price(ticker)
                asset_updates.append({"type": "stock", "id": ticker, "data": data})
            except Exception as e:
                print(f"Error fetching stock {ticker}: {e}")
                
        for scheme_code in mfs:
            try:
                data = await get_mf_nav(scheme_code)
                asset_updates.append({"type": "mf", "id": scheme_code, "data": data})
            except Exception as e:
                print(f"Error fetching mf {scheme_code}: {e}")
                
        for update in asset_updates:
            try:
                asset_type = update["type"]
                asset_id = update["id"]
                data = update["data"]
                
                name = data.get("name") or data.get("scheme_name")
                price = data.get("price") or data.get("nav")
                change_pct = data.get("change_pct", 0.0)
                
                await db.price_history.insert_one({
                    "asset_type": asset_type,
                    "asset_id": asset_id,
                    "price": price,
                    "previous_price": data.get("previous_close") or data.get("previous_nav"),
                    "change_pct": change_pct,
                    "recorded_at": datetime.now(timezone.utc)
                })
                
                # Check users tracking this asset
                for w in watchlists:
                    user_id = w["user_id"]
                    is_tracking = False
                    if asset_type == "stock":
                        is_tracking = any(s['ticker'] == asset_id for s in w.get('stocks', []))
                    else:
                        is_tracking = any(m['scheme_code'] == asset_id for m in w.get('mutual_funds', []))
                        
                    if is_tracking:
                        user = await db.users.find_one({"_id": ObjectId(user_id)})
                        if not user:
                            continue
                            
                        user_settings = user.get("settings", {})
                        threshold = user_settings.get(f"disaster_threshold_{asset_type}", 
                                                      settings.DISASTER_THRESHOLD_STOCK if asset_type == 'stock' else settings.DISASTER_THRESHOLD_MF)
                        
                        if change_pct <= -abs(threshold):
                            # Check alert log
                            two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
                            recent_alert = await db.alert_log.find_one({
                                "asset_type": asset_type,
                                "asset_id": asset_id,
                                "alerted_users": user_id,
                                "sent_at": {"$gt": two_hours_ago}
                            })
                            
                            if not recent_alert:
                                ai_analysis = await analyze_asset({
                                    "name": name,
                                    "asset_type": asset_type,
                                    "current_price": price,
                                    "previous_price": data.get("previous_close") or data.get("previous_nav"),
                                    "change_pct": change_pct,
                                    "is_alert": True
                                })
                                
                                html_body = build_alert_html(
                                    user_name=user.get("name", "User"),
                                    asset_name=name,
                                    asset_type=asset_type,
                                    change_pct=change_pct,
                                    current_price=price,
                                    ai_analysis=ai_analysis
                                )
                                
                                email_sent = await send_email(
                                    to_email=user.get("email"),
                                    subject=f"⚠️ Tracker Alert: {name} Drop",
                                    html_body=html_body
                                )
                                
                                if email_sent:
                                    await db.alert_log.insert_one({
                                        "asset_type": asset_type,
                                        "asset_id": asset_id,
                                        "change_pct": change_pct,
                                        "alerted_users": [user_id],
                                        "ai_analysis": ai_analysis,
                                        "sent_at": datetime.now(timezone.utc)
                                    })
            except Exception as e:
                print(f"Error processing update for {update['id']}: {e}")
                
    except Exception as e:
        print(f"Error in disaster_monitor: {e}")

async def send_scheduled_report(user_id: str):
    try:
        db = get_db()
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return
            
        w = await db.watchlists.find_one({"user_id": user_id})
        if not w:
            return
            
        assets_data = []
        for s in w.get('stocks', []):
            try:
                data = await get_stock_price(s['ticker'])
                assets_data.append({
                    "name": data["name"],
                    "asset_type": "stock",
                    "current_price": data["price"],
                    "previous_price": data["previous_close"],
                    "change_pct": data["change_pct"]
                })
            except Exception:
                pass
                
        for m in w.get('mutual_funds', []):
            try:
                data = await get_mf_nav(m['scheme_code'])
                assets_data.append({
                    "name": data["scheme_name"],
                    "asset_type": "mf",
                    "current_price": data["nav"],
                    "previous_price": data["previous_nav"],
                    "change_pct": data["change_pct"]
                })
            except Exception:
                pass
                
        if assets_data:
            ai_report = await generate_portfolio_report(assets_data)
            html_body = build_report_html(user.get("name", "User"), assets_data, ai_report)
            
            await send_email(
                to_email=user.get("email"),
                subject="TrackBucks Portfolio Report",
                html_body=html_body
            )
            
            for a in assets_data:
                await db.price_history.insert_one({
                    "asset_type": a["asset_type"],
                    "asset_id": a.get("name", "unknown"),
                    "price": a["current_price"],
                    "previous_price": a["previous_price"],
                    "change_pct": a["change_pct"],
                    "recorded_at": datetime.now(timezone.utc)
                })
                
    except Exception as e:
        print(f"Error in send_scheduled_report for user {user_id}: {e}")

async def reschedule_user_report(user_id: str, frequency: str, report_time: str):
    global scheduler
    if not scheduler:
        return
        
    job_id = f"report_{user_id}"
    
    # Remove existing job
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        
    try:
        hour, minute = map(int, report_time.split(':'))
    except ValueError:
        hour, minute = 18, 0
        
    if frequency == 'daily':
        trigger = CronTrigger(hour=hour, minute=minute)
    elif frequency == 'every_12h':
        trigger = IntervalTrigger(hours=12)
    elif frequency == 'every_6h':
        trigger = IntervalTrigger(hours=6)
    elif frequency == 'weekly':
        trigger = CronTrigger(day_of_week='mon', hour=hour, minute=minute)
    else:
        return
        
    scheduler.add_job(send_scheduled_report, trigger, args=[user_id], id=job_id)

async def load_all_user_schedules():
    try:
        db = get_db()
        users = await db.users.find().to_list(length=None)
        for user in users:
            settings_obj = user.get("settings", {})
            frequency = settings_obj.get("report_frequency")
            report_time = settings_obj.get("report_time", "18:00")
            if frequency:
                await reschedule_user_report(str(user["_id"]), frequency, report_time)
    except Exception as e:
        print(f"Error loading schedules: {e}")

async def start_scheduler():
    global scheduler
    scheduler = AsyncIOScheduler()
    
    interval = getattr(settings, 'POLL_INTERVAL_MINUTES', 15)
    scheduler.add_job(disaster_monitor, IntervalTrigger(minutes=interval), id="disaster_monitor")
    
    scheduler.start()
    await load_all_user_schedules()

async def stop_scheduler():
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown()
