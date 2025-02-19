import logging
from fastapi import APIRouter, HTTPException, Request
from psycopg2 import Error as DBError
from database import (get_user, reset_api_key, get_db)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

async def is_admin_user(request: Request, block: bool = True) -> bool:
    """
    Check if the user is an admin based on the OAuth token.
    
    Args:
        request: The FastAPI request object
        block: If True (default), blocks non-admins with HTTPException. If False, returns False instead.
    """
    oauth_token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if not oauth_token:
        if block:
            raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
        return False

    logger.info(f"Attempting to authenticate admin with OAuth token: {oauth_token[:10]}...")
    
    try:
        cursor = get_db().cursor()
        cursor.execute("SELECT * FROM users WHERE linuxdo_token = %s", (oauth_token,))
        user = cursor.fetchone()
        
    except DBError as e:
        logger.error(f"Database error in is_admin_user: {e}")
        raise HTTPException(status_code=500, detail="数据库查询失败") from e
    except Exception as e:
        logger.error(f"Unexpected error in is_admin_user: {e}")
        raise HTTPException(status_code=500, detail="系统错误") from e

    # Authentication and authorization logic (outside try-except)
    if not user:
        if block:
            raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
        return False
        
    if not user[4]:  # enabled column
        if block:
            raise HTTPException(status_code=403, detail=f"你的账户已被禁用，原因: {user[5]}")
        return False
        
    is_admin = bool(user[8])  # is_admin column
    if not is_admin and block:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    return is_admin
     

@router.post("/auth/reset")
async def reset_api(request: Request):
    """Reset the API key for the current user."""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not api_key:
        raise HTTPException(status_code=403, detail="Authorization header required")

    user = get_user(api_key=api_key)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user[4]:  # If user is disabled
        raise HTTPException(status_code=403, detail=f"User disabled: {user[5]}")

    user_id = user[0]
    new_key = reset_api_key(user_id)

    if not new_key:
        raise HTTPException(status_code=500, detail="Failed to reset API key")

    return { "apiKey": new_key }