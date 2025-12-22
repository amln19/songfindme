import psycopg2
from psycopg2.extras import execute_values
import logging
from typing import List, Tuple, Optional, Dict, Any
from .config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

logger = logging.getLogger("shazam")

# PostgreSQL connection parameters
DB_PARAMS = {
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "host": DB_HOST,
    "port": DB_PORT
}

def get_db_connection():
    """Get a new PostgreSQL connection"""
    return psycopg2.connect(**DB_PARAMS)

def init_db():
    """Create tables if they don't exist"""
    conn = get_db_connection()
    cur = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'user' 
        )
    """)
    
    # Songs table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS songs (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            artist VARCHAR(255),
            duration_seconds INT
        )
    """)

    # Fingerprints table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fingerprints (
            id SERIAL PRIMARY KEY,
            song_id INT NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
            hash BIGINT NOT NULL,
            offset_time BIGINT NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fingerprint_hash ON fingerprints(hash)")

    # History table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            song_id INT NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
            identified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Database initialized")

def insert_song(title: str, artist: str, duration_seconds: int) -> int:
    """Insert a song and return its ID"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO songs (title, artist, duration_seconds) VALUES (%s, %s, %s) RETURNING id",
            (title, artist, duration_seconds)
        )
        song_id = cur.fetchone()[0]
        conn.commit()
        logger.info(f"Inserted song: {title} by {artist}, ID={song_id}")
        return song_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Error inserting song: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def insert_fingerprints(song_id: int, fingerprints: List[Tuple[int, int]]) -> None:
    """
    Insert multiple fingerprints
    fingerprints: list of tuples (hash, offset_time)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        records = [(song_id, int(h), int(o)) for h, o in fingerprints]
        execute_values(
            cur,
            "INSERT INTO fingerprints (song_id, hash, offset_time) VALUES %s",
            records
        )
        conn.commit()
        logger.info(f"Inserted {len(fingerprints)} fingerprints for song_id={song_id}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error inserting fingerprints: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def insert_song_with_fingerprints(title: str, artist: str, duration_seconds: int, fingerprints: List[Tuple[int, int]]) -> int:
    """
    Atomically insert a song and its fingerprints in a single transaction
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Insert song
        cur.execute(
            "INSERT INTO songs (title, artist, duration_seconds) VALUES (%s, %s, %s) RETURNING id",
            (title, artist, duration_seconds)
        )
        song_id = cur.fetchone()[0]
        
        # Insert fingerprints
        records = [(song_id, int(h), int(o)) for h, o in fingerprints]
        execute_values(
            cur,
            "INSERT INTO fingerprints (song_id, hash, offset_time) VALUES %s",
            records
        )
        
        conn.commit()
        logger.info(f"Inserted song '{title}' with ID {song_id} and {len(fingerprints)} fingerprints")
        return song_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Transaction failed: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def get_matching_hashes(hashes: List[int]) -> List[Tuple[int, int, int]]:
    """
    Query fingerprints that match given hashes
    Returns list of tuples: (song_id, hash, offset_time)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT song_id, hash, offset_time FROM fingerprints WHERE hash = ANY(%s)",
        (hashes,)
    )
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results

def get_song_by_id(song_id: int) -> Optional[Tuple[str, str]]:
    """Get song title and artist by ID"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT title, artist FROM songs WHERE id = %s",
        (song_id,)
    )
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result

def create_user(username: str, password_hash: str, role: str = "user") -> Optional[int]:
    """Create a new user with validation"""
    if len(username) < 3 or len(username) > 50:
        raise ValueError("Username must be between 3 and 50 characters")
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) RETURNING id",
            (username, password_hash, role)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        return user_id
    except psycopg2.IntegrityError:
        conn.rollback()
        return None  # Username already exists
    finally:
        cur.close()
        conn.close()

def get_user_by_username(username: str) -> Optional[Tuple[int, str, str, str]]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash, role FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user # Returns tuple (id, username, hash, role) or None

def insert_history(user_id: int, song_id: int) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO history (user_id, song_id) VALUES (%s, %s)",
        (user_id, song_id)
    )
    conn.commit()
    cur.close()
    conn.close()

def get_user_history(user_id: int) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()
    # Fetch song details ordered by most recent first
    query = """
        SELECT s.title, s.artist, h.identified_at
        FROM history h
        JOIN songs s ON h.song_id = s.id
        WHERE h.user_id = %s
        ORDER BY h.identified_at DESC
    """
    cur.execute(query, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    # Convert datetime to string for JSON serialization
    return [{"title": r[0], "artist": r[1], "date": r[2].isoformat()} for r in rows]