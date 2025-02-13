import sqlite3
import os
import toml
import sys
import logging
import uuid
from typing import Optional

# Determine the project root directory
file_path = os.path.abspath(sys.argv[0])
file_dir = os.path.dirname(file_path)

# Construct the path to the config.toml file
config_path = os.path.join(file_dir, "config.toml")

# Load the configuration
config = toml.load(config_path)

# Database Configuration
db_path = config.get("db_path", "poe-to-gpt.db")  # SQLite database path

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
    if _db is not None:
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
           'is_admin', 'reset_api_key', 'get_all_users', 'disable_user', 'enable_user']

def create_connection():
    """Create a database connection to a SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        logger.info(f"Connected to SQLite database: {db_path}")
    except sqlite3.Error as e:
        logger.error(f"Error connecting to SQLite database: {e}")
    return conn

def create_table():
    """Create a table in the SQLite database."""
    try:
        sql_create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            api_key TEXT UNIQUE NOT NULL,
            username TEXT,
            linuxdo_token TEXT,
            enabled INTEGER DEFAULT 1,
            disable_reason TEXT,
            created_at TEXT,
            last_used_at TEXT,
            is_admin INTEGER DEFAULT 0
        );
        """
        cursor = _db.cursor()  # Use global connection
        cursor.execute(sql_create_users_table)
        _db.commit()
        # Only log if the table was actually created
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        if len(columns) > 0:
            logger.info("Users table created successfully")
    except sqlite3.Error as e:
        logger.error(f"Error creating table: {e}")

def get_user(api_key: str):
    """Get a user from the database by api_key."""
    try:
        cursor = _db.cursor()  # Use global connection
        cursor.execute("SELECT * FROM users WHERE api_key=?", (api_key,))
        user = cursor.fetchone()
        return user
    except sqlite3.Error as e:
        logger.error(f"Error getting user: {e}")
        return None
    
def get_user_by_id(user_id: int):
    """Get a user from the database by user_id."""
    try:
        cursor = _db.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = cursor.fetchone()
        return user
    except sqlite3.Error as e:
        logger.error(f"Error getting user: {e}")
        return None

def create_user(user_id, api_key: str, username: str, linuxdo_token: str):
    """Create a new user in the database."""
    try:
        sql = ''' INSERT INTO users(user_id, api_key, username, linuxdo_token, created_at)
                  VALUES(?,?,?,?,NOW()) '''
        cursor = _db.cursor()  # Use global connection
        cursor.execute(sql, (user_id, api_key, username, linuxdo_token))
        _db.commit()
        logger.info(f"User created successfully: {username}")
        return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Error creating user: {e}")
        return None

def reset_api_key(user_id: int) -> Optional[str]:
    """Reset a user's API key."""
    try:
        new_api_key = f"sk-yn-{uuid.uuid4()}"
        cursor = _db.cursor()
        cursor.execute("UPDATE users SET api_key=? WHERE user_id=?", (new_api_key, user_id))
        _db.commit()
        return new_api_key
    except sqlite3.Error as e:
        logger.error(f"Error resetting API key: {e}")
        return None

def get_all_users():
    """Get all users from database."""
    try:
        cursor = _db.cursor()
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Error getting users: {e}")
        return []

def disable_user(user_id: int, reason: str) -> bool:
    """Disable a user's access."""
    try:
        cursor = _db.cursor()
        cursor.execute("UPDATE users SET enabled=0, disable_reason=? WHERE user_id=?", (reason, user_id))
        _db.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error disabling user: {e}")
        return False

def enable_user(user_id: int) -> bool:
    """Re-enable a user's access."""
    try:
        cursor = _db.cursor()
        cursor.execute("UPDATE users SET enabled=1, disable_reason=NULL WHERE user_id=?", (user_id,))
        _db.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error enabling user: {e}")
        return False
