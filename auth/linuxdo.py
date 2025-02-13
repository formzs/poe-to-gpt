import json
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from authlib.integrations.starlette_client import OAuth
import toml
import os
import sys
import logging
# Import the database module and functions
from database import (create_user, get_user_by_id, update_linuxdo_token)
import datetime
import uuid
from httpx import AsyncClient

router = APIRouter()

# Determine the project root directory
file_path = os.path.abspath(sys.argv[0])
file_dir = os.path.dirname(file_path)

# Construct the path to the config.toml file
config_path = os.path.join(file_dir, "config.toml")

# Load the configuration
config = toml.load(config_path)

# LinuxDO OAuth Configuration
base_url = config.get("base_url", "http://localhost:3700")  # Your application's base URL
LINUXDO_CLIENT_KEY = config.get("LINUXDO_CLIENT_KEY")
LINUXDO_CLIENT_SECRET = config.get("LINUXDO_CLIENT_SECRET")

# Setup OAuth
# config = Config({'LINUXDO_CLIENT_ID': LINUXDO_CLIENT_KEY, 'LINUXDO_CLIENT_SECRET': LINUXDO_CLIENT_SECRET})
oauth = OAuth()
oauth.register(
    name='linuxdo',
    authorize_url='https://connect.linux.do/oauth2/authorize',
    access_token_url='https://connect.linux.do/oauth2/token',
    client_id=LINUXDO_CLIENT_KEY,
    client_secret=LINUXDO_CLIENT_SECRET,
    client_kwargs={'scope': 'openid profile email'}
)

# Optionally define UserUrl
UserUrl = "https://connect.linux.do/api/user"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Function to generate a secure API key
def generate_api_key():
    return f"sk-yn-{uuid.uuid4()}"

# OAuth routes
@router.get('/auth/linuxdo')
async def auth_linuxdo(request: Request, self: str = None):
    """Handle LinuxDO authentication."""
    redirect_uri = base_url + '/oauth/callback'  # This must match the registered redirect URI
    return await oauth.linuxdo.authorize_redirect(request, redirect_uri)

@router.get('/oauth/callback')
async def authorize(request: Request):
    try:
        token = await oauth.linuxdo.authorize_access_token(request)
        logger.info("Received token response: %s", token)
        
        # Get access token
        access_token = token.get('access_token')
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")

        # Fetch user info directly from LinuxDO API
        async with AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(UserUrl, headers=headers)
            response.raise_for_status()
            user_info = response.json()

        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to fetch user info")

        # Extract relevant user information
        username = user_info.get('username')
        user_id = user_info.get('id')

        logger.info(f"Received user info: {user_info}")
  
        user = get_user_by_id(user_id)

        if not user:
            # Create a new user
            api_key = generate_api_key()
            user = create_user(user_id, api_key, username, access_token)
        else:
            # Update the user's linuxdo_token
            update_linuxdo_token(user_id, access_token)
            api_key = user[1]

        # check if user is disabled
        if not user[4]:
            # If user is disabled, raise an error with reason
            raise HTTPException(status_code=403, detail=f'User is disabled: {user[5]}')

        # Check if the user is an admin
        res = {
            "apiKey": api_key,
            "oauth_token": access_token,
            "admin": user[3]
        }

        return HTMLResponse(f"""
            <script>
                window.opener.postMessage({json.dumps(res)}, window.location.origin);
                window.close();
            </script>
        """)

    except Exception as e:
        logger.error(f"OAuth authorization failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))