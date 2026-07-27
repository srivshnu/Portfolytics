import bcrypt
from itsdangerous import URLSafeSerializer, BadSignature
from fastapi import Request
from fastapi.responses import RedirectResponse
from config import settings
from database import get_db
from bson import ObjectId

_serializer = URLSafeSerializer(settings.SECRET_KEY, salt="session")


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_session(response, user_id: str):
    token = _serializer.dumps(user_id)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,  # 7 days
        samesite="lax",
    )
    return response


def clear_session(response):
    response.delete_cookie("session_token")
    return response


async def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        return None
    try:
        user_id = _serializer.loads(token)
    except BadSignature:
        return None
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user:
        user["id"] = str(user["_id"])
    return user


async def require_auth(request: Request):
    user = await get_current_user(request)
    if not user:
        raise RedirectToLogin()
    return user


class RedirectToLogin(Exception):
    pass


def set_flash(response, message: str, flash_type: str = "success"):
    response.set_cookie("flash_message", message, max_age=10, httponly=True, samesite="lax")
    response.set_cookie("flash_type", flash_type, max_age=10, httponly=True, samesite="lax")
    return response


def get_flash(request: Request):
    message = request.cookies.get("flash_message")
    flash_type = request.cookies.get("flash_type", "success")
    return message, flash_type


def clear_flash(response):
    response.delete_cookie("flash_message")
    response.delete_cookie("flash_type")
    return response
