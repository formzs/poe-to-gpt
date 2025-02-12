from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
import toml
import os
import sys
import logging
# Import the database module and functions
from database import get_user, create_user, get_db
import datetime
import uuid

router = APIRouter()

# Determine the project root directory
file_path = os.path.abspath(sys.argv[0])
file_dir = os.path.dirname(file_path)

# Construct the path to the config.toml file
config_path = os.path.join(file_dir, "config.toml")

# Load the configuration
config = toml.load(config_path)

# LinuxDO OAuth Configuration
base_url = config.get("base_url", "https://localhost:3700")  # Your application's base URL
LINUXDO_CLIENT_KEY = config.get("LINUXDO_CLIENT_KEY")
LINUXDO_CLIENT_SECRET = config.get("LINUXDO_CLIENT_SECRET")

# Setup OAuth
# config = Config({'LINUXDO_CLIENT_ID': LINUXDO_CLIENT_KEY, 'LINUXDO_CLIENT_SECRET': LINUXDO_CLIENT_SECRET})
oauth = OAuth()
oauth.register(
    name='linuxdo',
    server_metadata_url='https://connect.linux.do/oauth/discovery',
    client_id=LINUXDO_CLIENT_KEY,
    client_secret=LINUXDO_CLIENT_SECRET,
    client_kwargs={'scope': 'openid profile email'}
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Function to generate a secure API key
def generate_api_key():
    return f"sk-yn-{uuid.uuid4()}"

# OAuth route
@router.get('/login')
async def login(request: Request):
    redirect_uri = base_url + '/oauth/callback'  # This must match the registered redirect URI
    return await oauth.linuxdo.authorize_redirect(request, redirect_uri)

@router.get('/oauth/callback')
async def authorize(request: Request):
    try:
        token = await oauth.linuxdo.authorize_access_token(request)
    except Exception as e:
        logger.error(f"OAuth authorization failed: {e}")
        raise HTTPException(status_code=400, detail="OAuth authorization failed")
    user_info = token.get('userinfo')
    access_token = token.get('access_token')
    if user_info:
        linuxdo_id = user_info.get('sub')
        email = user_info.get('email')
        name = user_info.get('name')
        
        db_user = get_user(access_token)  # No need to pass db
        if db_user:
            logger.info(f"User already exists in the database: {linuxdo_id}")
        else:
            api_key = generate_api_key()
            now = datetime.datetime.now().isoformat()
            create_user(api_key, name, access_token, now)  # No need to pass db
            logger.info(f"Created user with API key: {api_key[:10]}...")
            # Redirect to a success page with the API key
            success_url = f"{base_url}/login/success?api_key={api_key}"
            return RedirectResponse(url=success_url)

        logger.info(f"Logged in user: {user_info}")
        # Redirect to a page indicating successful login
        return RedirectResponse(url=base_url + '/login/success')
    else:
        raise HTTPException(status_code=400, detail="Failed to retrieve user info")

@router.get('/login/success')
async def login_success(api_key: str = None):
    if api_key:
        return f"Login Success! Your API key is: {api_key}"
    else:
        return "Login Success!"
