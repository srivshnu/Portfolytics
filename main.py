import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from config import settings
from database import connect_db, close_db
from auth import RedirectToLogin
from routes import pages, auth_routes, watchlist_routes, settings_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    # Start scheduler after DB is ready
    from services.scheduler_service import start_scheduler
    await start_scheduler()
    print("[Portfolytics] Server ready.")
    yield
    from services.scheduler_service import stop_scheduler
    await stop_scheduler()
    await close_db()


app = FastAPI(title="Portfolytics", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(pages.router)
app.include_router(auth_routes.router)
app.include_router(watchlist_routes.router)
app.include_router(settings_routes.router)


@app.exception_handler(RedirectToLogin)
async def redirect_to_login_handler(request: Request, exc: RedirectToLogin):
    return RedirectResponse(url="/login", status_code=302)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
