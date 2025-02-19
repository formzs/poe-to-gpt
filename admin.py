from fastapi import APIRouter, Depends, HTTPException, Request
from database import (get_user, get_db, reset_api_key,
                      disable_user, enable_user)
import logging
from auth.auth import is_admin_user

router = APIRouter(prefix="/api")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@router.post("/admin/reset-key/{user_id}")
async def admin_reset_key(user_id: int, is_admin: bool = Depends(is_admin_user)):
    """Reset a user's API key."""
    new_key = reset_api_key(user_id)
    if new_key:
        return {
            "success": True,
            "message": "API密钥已重置",
            "new_key": new_key
        }
    raise HTTPException(status_code=500, detail="重置API密钥失败")

@router.post("/admin/disable/{user_id}")
async def admin_disable_user(
    user_id: int, 
    data: dict,
    is_admin: bool = Depends(is_admin_user)
):
    """Disable a user's access."""
    reason = data.get('reason')
    if not reason:
        raise HTTPException(status_code=400, detail="禁用原因不能为空")
        
    if disable_user(user_id, reason):
        logger.info(f"User {user_id} disabled with reason: {reason}")
        return {
            "success": True, 
            "message": "用户已被禁用"
        }
    raise HTTPException(status_code=500, detail="禁用用户失败")

@router.post("/admin/enable/{user_id}")
async def admin_enable_user(user_id: int, is_admin: bool = Depends(is_admin_user)):
    """Re-enable a user's access."""
    if enable_user(user_id):
        return {"success": True, "message": "用户已启用"}
    raise HTTPException(status_code=500, detail="启用用户失败")

@router.post("/admin/toggle-admin/{user_id}")
async def toggle_admin(user_id: int, request: Request, is_admin: bool = Depends(is_admin_user)):
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
        
        # Add success message in response
        return {
            "success": True,
            "message": "管理员权限已{}".format("赋予" if new_admin_status else "撤销")
        }
    except Exception as e:
        logger.error(f"Failed to update admin status: {e}")
        raise HTTPException(status_code=500, detail="更新管理员状态失败")

@router.get("/users")
async def list_users(
    is_admin: bool = Depends(is_admin_user),
    search: str = None,
    status: str = None,
    admin_filter: str = None,
    sort_by: str = None,
    sort_dir: str = "asc"
):
    """List all users with filtering, sorting and searching."""
    try:
        cursor = get_db().cursor()
        
        # Base query
        query = "SELECT * FROM users"
        conditions = []
        params = []

        # Add search condition
        if search:
            conditions.append("(CAST(user_id AS TEXT) LIKE %s OR LOWER(username) LIKE %s)")
            search_term = f"%{search.lower()}%"
            params.extend([search_term, search_term])

        # Add status filter
        if status:
            if status == "enabled":
                conditions.append("enabled = TRUE")
            elif status == "disabled":
                conditions.append("enabled = FALSE")

        # Add admin filter
        if admin_filter:
            if admin_filter == "admin":
                conditions.append("is_admin = TRUE")
            elif admin_filter == "user":
                conditions.append("is_admin = FALSE")

        # Combine conditions
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Add sorting
        valid_sort_fields = {
            'username': 'username',
            'user_id': 'user_id',
            'created_at': 'created_at',
            'last_used_at': 'last_used_at'
        }
        
        if sort_by in valid_sort_fields:
            sort_direction = "DESC" if sort_dir.lower() == "desc" else "ASC"
            query += f" ORDER BY {valid_sort_fields[sort_by]} {sort_direction}"
        else:
            query += " ORDER BY created_at DESC"  # Default sorting

        logger.debug(f"Executing query: {query} with params: {params}")
        cursor.execute(query, params)
        users = cursor.fetchall()

        user_list = [{
            "user_id": user[0],
            "username": user[2],
            "enabled": user[4],
            "disable_reason": user[5],
            "is_admin": user[8],
            "created_at": user[6],
            "last_used_at": user[7]
        } for user in users]

        return {"users": user_list}

    except Exception as e:
        logger.error(f"Database error in list_users: {e}")
        raise HTTPException(status_code=500, detail="数据库查询失败")

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

