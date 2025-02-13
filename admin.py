from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from database import (get_user, create_user, get_db, is_admin, reset_api_key, 
                     get_all_users, disable_user, enable_user)

router = APIRouter()

@router.post("/admin/reset-key/{user_id}")
async def admin_reset_key(user_id: int, request: Request):
    """Reset a user's API key."""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not api_key or not is_admin(api_key):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    new_key = reset_api_key(user_id)
    if new_key:
        return {"success": True, "new_key": new_key}
    raise HTTPException(status_code=500, detail="Failed to reset API key")

@router.post("/admin/disable/{user_id}")
async def admin_disable_user(user_id: int, request: Request, reason: str = Form(...)):
    """Disable a user's access."""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not api_key or not is_admin(api_key):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if disable_user(user_id, reason):
        return RedirectResponse(url="/admin", status_code=303)
    raise HTTPException(status_code=500, detail="Failed to disable user")

@router.post("/admin/enable/{user_id}")
async def admin_enable_user(user_id: int, request: Request):
    """Re-enable a user's access."""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not api_key or not is_admin(api_key):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if enable_user(user_id):
        return RedirectResponse(url="/admin", status_code=303)
    raise HTTPException(status_code=500, detail="Failed to enable user")

@router.get("/api/users")
async def list_users(request: Request):
    """List all users (admin only)."""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not api_key or not is_admin(api_key):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = get_all_users()
    user_list = [{"user_id": user[0], "username": user[2], "enabled": user[4]} for user in users]
    return {"users": user_list}

@router.post("/api/users/{user_id}/toggle")
async def toggle_user(user_id: int, request: Request):
    """Enable or disable a user (admin only)."""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not api_key or not is_admin(api_key):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = get_user(user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user[4]:  # If user is enabled
        if disable_user(user_id, "Disabled by admin"):
            return {"success": True, "message": "User disabled"}
        else:
            raise HTTPException(status_code=500, detail="Failed to disable user")
    else:  # If user is disabled
        if enable_user(user_id):
            return {"success": True, "message": "User enabled"}
        else:
            raise HTTPException(status_code=500, detail="Failed to enable user")

@router.get("/api/roles")
async def list_roles(request: Request):
    """List all roles (admin only)."""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not api_key or not is_admin(api_key):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Replace this with your actual role fetching logic
    roles = [{"role_id": 1, "role_name": "admin"}, {"role_id": 2, "role_name": "user"}]
    return {"roles": roles}
