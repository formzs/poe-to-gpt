import logging
import os
import sys

from fastapi import APIRouter, HTTPException, Request
import toml
from database import (get_user, reset_api_key)

# Determine the project root directory
file_path = os.path.abspath(sys.argv[0])
file_dir = os.path.dirname(file_path)


# Construct the path to the config.toml file
config_path = os.path.join(file_dir, "config.toml")

# Load the configuration
config = toml.load(config_path)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

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
        raise HTTPException(status_code=403, detail=f"User disabled: {user[3]}")

    new_key = reset_api_key(api_key)

    return { "apiKey": new_key }