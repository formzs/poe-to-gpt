import os
import toml
import sys
import logging
import uuid
from typing import Optional
import psycopg2  # Import psycopg2
from urllib.parse import urlparse
import time

# Determine the project root directory
file_path = os.path.abspath(sys.argv[0])
file_dir = os.path.dirname(file_path)

# Construct the path to the config.toml file
config_path = os.path.join(file_dir, "config.toml")

# Load the configuration
config = toml.load(config_path)

# Database Configuration
db_url = config.get("db_url", "postgresql://user:password@host/database")  # PostgreSQL database URL

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global database connection
_db = None

def get_db():
    """Get the global database connection."""
    return _db

def init_db():
    """Initialize the global database connection."""
    global _db
    _db = create_connection()
    if (_db):
        create_table()  # No need to pass _db
    return _db

def close_db():
    """Close the global database connection."""
    global _db
    if (_db):
        _db.close()
        _db = None

# Make these functions available for import
__all__ = ['init_db', 'get_db', 'close_db', 'get_user', 'create_user', 
           'is_admin', 'reset_api_key', 'get_all_users', 'disable_user', 'enable_user', 'update_linuxdo_token']

def create_connection():
    """Create a database connection to a PostgreSQL database."""
    conn = None
    try:
        # Parse the database URL
        result = urlparse(db_url)
        username = result.username
        password = result.password
        database = result.path[1:]
        hostname = result.hostname
        sslmode = 'require' if result.query == 'sslmode=require' else 'disable'

        # Log connection parameters (excluding password)
        logger.info(f"Connecting to PostgreSQL database: host={hostname}, database={database}, user={username}, sslmode={sslmode}")

        conn = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            sslmode=sslmode
        )

        # Check if the connection is valid
        if conn.status == psycopg2.extensions.STATUS_READY:
            logger.info(f"Successfully connected to PostgreSQL database: {db_url}")
            return conn
        else:
            logger.error("Failed to establish a valid connection to PostgreSQL.")
            return None

    except psycopg2.Error as e:
        logger.error(f"psycopg2 Error connecting to PostgreSQL database: {e}")
        return None
    except Exception as e:
        logger.error(f"General error connecting to PostgreSQL database: {e}")
        return None
    return conn

def create_table():
    """Create a table in the PostgreSQL database."""
    try:
        sql_create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            api_key TEXT UNIQUE NOT NULL,
            username TEXT,
            linuxdo_token TEXT,
            enabled BOOLEAN DEFAULT TRUE,
            disable_reason TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP WITHOUT TIME ZONE,
            is_admin BOOLEAN DEFAULT FALSE
        );
        """
        cursor = _db.cursor()  # Use global connection
        cursor.execute(sql_create_users_table)
        _db.commit()
        logger.info("Users table created successfully")
    except psycopg2.Error as e:
        logger.error(f"Error creating table: {e}")

def get_user(api_key: str):
    """Get a user from the database by api_key."""
    try:
        cursor = _db.cursor()  # Use global connection
        cursor.execute("SELECT * FROM users WHERE api_key=%s", (api_key,))
        user = cursor.fetchone()
        return user
    except psycopg2.Error as e:
        logger.error(f"Error getting user: {e}")
        return None
    
def get_user_by_id(user_id: int):
    """Get a user from the database by user_id."""
    try:
        cursor = _db.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id=%s", (int(user_id),),)
        user = cursor.fetchone()
        return user
    except psycopg2.Error as e:
        logger.error(f"Error getting user: {e}")
        return None

def create_user(api_key: str, username: str, linuxdo_token: str):
    """Create a new user in the database."""
    try:
        sql = ''' INSERT INTO users(api_key, username, linuxdo_token, created_at)
                  VALUES(%s, %s, %s, CURRENT_TIMESTAMP) '''
        cursor = _db.cursor()  # Use global connection
        cursor.execute(sql, (api_key, username, linuxdo_token))
        _db.commit()
        logger.info(f"User created successfully: {username}")
        return cursor.lastrowid
    except psycopg2.Error as e:
        logger.error(f"Error creating user: {e}")
        return None

def reset_api_key(user_id: int) -> Optional[str]:
    """Reset a user's API key."""
    try:
        new_api_key = f"sk-yn-{uuid.uuid4()}"
        cursor = _db.cursor()
        cursor.execute("UPDATE users SET api_key=%s WHERE user_id=%s", (new_api_key, int(user_id)),)
        _db.commit()
        return new_api_key
    except psycopg2.Error as e:
        logger.error(f"Error resetting API key: {e}")
        return None

def get_all_users():
    """Get all users from database."""
    try:
        cursor = _db.cursor()
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        return cursor.fetchall()
    except psycopg2.Error as e:
        logger.error(f"Error getting users: {e}")
        return []

def disable_user(user_id: int, reason: str) -> bool:
    """Disable a user's access."""
    try:
        cursor = _db.cursor()
        cursor.execute("UPDATE users SET enabled=FALSE, disable_reason=%s WHERE user_id=%s", (reason, int(user_id)),)
        _db.commit()
        return True
    except psycopg2.Error as e:
        logger.error(f"Error disabling user: {e}")
        return False

def enable_user(user_id: int) -> bool:
    """Re-enable a user's access."""
    try:
        cursor = _db.cursor()
        cursor.execute("UPDATE users SET enabled=TRUE, disable_reason=NULL WHERE user_id=%s", (int(user_id),))
        _db.commit()
        return True
    except psycopg2.Error as e:
        logger.error(f"Error enabling user: {e}")
        return False

def is_admin(api_key: str) -> bool:
    """Check if a user is an admin."""
    try:
        cursor = _db.cursor()
        cursor.execute("SELECT is_admin FROM users WHERE api_key=%s", (api_key,))
        user = cursor.fetchone()
        if user:
            return user[0] == 1
        return False
    except psycopg2.Error as e:
        logger.error(f"Error checking admin status: {e}")
        return False

def get_linuxdo_token(api_key: str) -> Optional[str]:
    """Get the linuxdo_token for a user."""
    try:
        cursor = _db.cursor()
        cursor.execute("SELECT linuxdo_token FROM users WHERE api_key=%s", (api_key,))
        user = cursor.fetchone()
        if user:
            return user[0]
        return None
    except psycopg2.Error as e:
        logger.error(f"Error getting linuxdo_token: {e}")
        return None

def update_linuxdo_token(user_id: int, linuxdo_token: str) -> bool:
    """Update a user's LinuxDO token."""
    try:
        cursor = _db.cursor()
        cursor.execute("UPDATE users SET linuxdo_token=%s WHERE user_id=%s", (linuxdo_token, int(user_id)))
        _db.commit()
        logger.info(f"User linuxdo_token updated successfully: {user_id}")
        return True
    except psycopg2.Error as e:
        logger.error(f"Error updating linuxdo_token: {e}")
        return False
