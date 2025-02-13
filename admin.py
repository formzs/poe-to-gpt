from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from database import (get_user,  get_db, reset_api_key,
                     get_all_users, disable_user, enable_user)
import logging
from auth.linuxdo import verify_linuxdo_token

# Update router prefix to handle admin API routes
router = APIRouter(prefix="/api")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def is_admin_user(request: Request):
    """Check if the user is an admin based on the OAuth token."""
    oauth_token = request.headers.get("Authorization", "").replace("Bearer ", "")
    logger.info(f"Attempting to authenticate admin with OAuth token: {oauth_token[:10]}...")
    if not oauth_token:
        raise HTTPException(status_code=403, detail="需要管理员权限：缺少登录令牌")

    # First verify the token with LinuxDO
    if not await verify_linuxdo_token(oauth_token):
        raise HTTPException(status_code=401, detail="访问令牌已过期或无效")

    # Look up user by linuxdo_token instead of api_key
    try:
        cursor = get_db().cursor()
        cursor.execute("SELECT * FROM users WHERE linuxdo_token = %s", (oauth_token,))
        user = cursor.fetchone()
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="数据库查询失败")

    if not user:
        raise HTTPException(status_code=403, detail="登录令牌无效，请重新登录")

    if not user[8]:  # is_admin column
        raise HTTPException(status_code=403, detail="权限不足：此账号不是管理员")

    logger.info(f"Admin access granted to user: {user[2]}")
    return True

@router.post("/admin/reset-key/{user_id}")
async def admin_reset_key(user_id: int, is_admin: bool = Depends(is_admin_user)):
    """Reset a user's API key."""
    new_key = reset_api_key(user_id)
    if new_key:
        return {"success": True, "new_key": new_key}
    raise HTTPException(status_code=500, detail="重置API密钥失败")

@router.post("/admin/disable/{user_id}")
async def admin_disable_user(user_id: int, reason: str = Form(...), is_admin: bool = Depends(is_admin_user)):
    """Disable a user's access."""
    if disable_user(user_id, reason):
        return RedirectResponse(url="/admin", status_code=303)
    raise HTTPException(status_code=500, detail="Failed to disable user")

@router.post("/admin/enable/{user_id}")
async def admin_enable_user(user_id: int, is_admin: bool = Depends(is_admin_user)):
    """Re-enable a user's access."""
    if enable_user(user_id):
        return RedirectResponse(url="/admin", status_code=303)
    raise HTTPException(status_code=500, detail="Failed to enable user")

@router.post("/admin/toggle-admin/{user_id}")
async def toggle_admin(user_id: int, request: Request):
    """Toggle admin status for a user (admin only)."""
    body = await request.json()
    new_admin_status = body.get('is_admin', False)
    
    try:
        cursor = get_db().cursor()
        cursor.execute(
            "UPDATE users SET is_admin = %s WHERE user_id = %s",
            (new_admin_status, user_id)
        )
        get_db().commit()
        return {"success": True, "message": "管理员状态已更新"}
    except Exception as e:
        logger.error(f"Failed to update admin status: {e}")
        raise HTTPException(status_code=500, detail="更新管理员状态失败")

@router.get("/users")
async def list_users(is_admin: bool = Depends(is_admin_user)):
    """List all users (admin only)."""
    users = get_all_users()
    user_list = [{
        "user_id": user[0],
        "username": user[2],
        "enabled": user[4],
        "disable_reason": user[5],  # Include disable_reason
        "is_admin": user[8],
        "created_at": user[6].isoformat() if user[6] else None,
        "last_used_at": user[7].isoformat() if user[7] else None
    } for user in users]
    return {"users": user_list}

@router.post("/users/{user_id}/toggle")
async def toggle_user(user_id: int, is_admin: bool = Depends(is_admin_user)):
    """Enable or disable a user (admin only)."""
    user = get_user(user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if user[4]:  # If user is enabled
        if disable_user(user_id, "管理员禁用"):
            return {"success": True, "message": "用户已禁用"}
        else:
            raise HTTPException(status_code=500, detail="禁用用户失败")
    else:  # If user is disabled
        if enable_user(user_id):
            return {"success": True, "message": "用户已启用"}
        else:
            raise HTTPException(status_code=500, detail="启用用户失败")
