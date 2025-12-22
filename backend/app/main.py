from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import logging
from datetime import timedelta

from .fingerprint import fingerprint
from .database import (
    init_db, 
    insert_song_with_fingerprints, 
    get_song_by_id, 
    create_user, 
    get_user_by_username, 
    insert_history, 
    get_user_history
)
from .match import match_clip
from .auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user, 
    get_current_admin, 
    get_optional_user
)
from .config import UPLOAD_DIR, CORS_ORIGINS, ACCESS_TOKEN_EXPIRE_MINUTES

# ---------------------------
# Logging configuration
# ---------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("shazam")

# ---------------------------
# App and upload dir
# ---------------------------
app = FastAPI(title="SongFindMe API", version="1.0.0")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------
# CORS Middleware
# ---------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Initialize Database on startup
# ---------------------------
@app.on_event("startup")
def startup_event():
    init_db()
    logger.info("Database initialized and ready!")
    logger.info(f"CORS origins: {CORS_ORIGINS}")

# ---------------------------
# Health Check Endpoint
# ---------------------------
@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify API is running.
    
    Returns:
        dict: Status message indicating service health
    """
    return {"status": "healthy", "service": "SongFindMe API"}

# ---------------------------
# Auth Endpoints (Register & Login)
# ---------------------------

@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...), role: str = Form("user")):
    """
    Create a new user account.
    
    Args:
        username: Desired username (3-50 characters)
        password: Password (minimum 6 characters)
        role: User role, either 'user' or 'admin' (defaults to 'user')
    
    Returns:
        dict: Success message with user_id
    
    Raises:
        HTTPException: If username exists or validation fails
    """
    # Sanitize username
    username = username.strip()
    
    # Check if user exists
    if get_user_by_username(username):
        raise HTTPException(status_code=400, detail="Username already registered")
    
    try:
        hashed_pw = get_password_hash(password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    try:
        user_id = create_user(username, hashed_pw, role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if user_id is None:
        raise HTTPException(status_code=400, detail="Registration failed")
    
    return {"message": f"User {username} created with role {role}", "user_id": user_id}

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token login endpoint.
    
    Args:
        form_data: OAuth2 form with username and password
    
    Returns:
        dict: Access token and token type
    
    Raises:
        HTTPException: If credentials are invalid
    """
    user = get_user_by_username(form_data.username)
    # user tuple: (id, username, hash, role)
    
    if not user or not verify_password(form_data.password, user[2]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Put the ROLE inside the token
    access_token = create_access_token(
        data={"sub": user[1], "role": user[3]}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# ---------------------------
# Add Song (API Endpoint)
# ---------------------------
@app.post("/add-song")
async def add_song(
    file: UploadFile = File(...), 
    title: str = Form(...), 
    artist: str = Form(...), 
    current_user: dict = Depends(get_current_admin)
):
    """
    Add a new song to the database (Admin only).
    
    Processes the audio file to generate fingerprints and stores
    them in the database for future identification.
    
    Args:
        file: Audio file (MP3, WAV, M4A, FLAC, OGG)
        title: Song title
        artist: Artist name
        current_user: Authenticated admin user
    
    Returns:
        dict: Success message with song_id and fingerprint count
    
    Raises:
        HTTPException: If user is not admin or processing fails
    """
    # Sanitize inputs
    title = title.strip()
    artist = artist.strip()
    
    if not title or not artist:
        raise HTTPException(status_code=400, detail="Title and artist cannot be empty")
    
    # Generate safe filename
    file_ext = os.path.splitext(file.filename)[1]
    safe_filename = f"{current_user['id']}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, safe_filename)

    # Save file
    try:
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Saved file to {path}")

        # Process file
        hashes, duration = fingerprint(path)
        logger.info(f"Generated {len(hashes)} fingerprints for '{title}'")

        if len(hashes) == 0:
            raise HTTPException(status_code=400, detail="No fingerprints generated. Audio may be too quiet or corrupted.")

        # Use atomic transaction
        song_id = insert_song_with_fingerprints(title, artist, int(duration), hashes)
        logger.info(f"Successfully added song '{title}' with ID {song_id}")

        return {
            "message": "Song added successfully", 
            "song_id": song_id, 
            "fingerprints": len(hashes)
        }
    
    except Exception as e:
        logger.error(f"Error processing song: {e}")
        raise HTTPException(status_code=500, detail="Failed to process audio file")
    
    finally:
        # Clean up uploaded file
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Cleaned up file: {path}")

# ---------------------------
# Identify Song (API Endpoint)
# ---------------------------
@app.post("/identify")
async def identify(file: UploadFile = File(...), current_user: dict = Depends(get_optional_user)):
    """
    Identify a song from an audio clip.
    
    Extracts fingerprints from the uploaded audio and matches them
    against the database. If user is logged in, saves to history.
    
    Args:
        file: Audio clip to identify (any format)
        current_user: Optional authenticated user (for history tracking)
    
    Returns:
        dict: Match results with song info, or null if no match
    
    Raises:
        HTTPException: If processing fails
    """
    # Generate safe filename
    safe_filename = f"identify_{file.filename}"
    path = os.path.join(UPLOAD_DIR, safe_filename)

    try:
        # Save file
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Saved clip to {path} for identification")

        hashes, _ = fingerprint(path)
        logger.info(f"Extracted {len(hashes)} fingerprints from clip")

        if len(hashes) == 0:
            return {
                "match_song_id": None,
                "matched_hashes_count": 0,
                "title": None,
                "artist": None,
                "message": "Could not extract fingerprints from audio"
            }

        song_id, matched_hashes = match_clip(hashes, return_matches=True)

        if song_id is None:
            logger.info("No matching song found")
            return {
                "match_song_id": None,
                "matched_hashes_count": 0,
                "title": None,
                "artist": None
            }

        logger.info(f"Matched song ID: {song_id} with {len(matched_hashes)} matching hashes")
        
        # Fetch song details
        song_info = get_song_by_id(song_id)
        title, artist = song_info if song_info else ("Unknown", "Unknown")

        # Save to history ONLY if user is logged in
        if current_user:
            logger.info(f"Saving match to history for user {current_user['username']}")
            insert_history(current_user['id'], song_id)

        return {
            "match_song_id": song_id,
            "matched_hashes_count": len(matched_hashes),
            "title": title,
            "artist": artist
        }
    
    except Exception as e:
        logger.error(f"Error identifying song: {e}")
        raise HTTPException(status_code=500, detail="Failed to identify song")
    
    finally:
        # Clean up uploaded file
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Cleaned up file: {path}")

# --- HISTORY ENDPOINT ---

@app.get("/history")
async def get_history(current_user: dict = Depends(get_current_user)):
    """
    Fetch identification history for the logged-in user.
    
    Returns all songs previously identified by the user,
    ordered by most recent first.
    
    Args:
        current_user: Authenticated user
    
    Returns:
        list: User's identification history with timestamps
    
    Raises:
        HTTPException: If user is not authenticated
    """
    history = get_user_history(current_user['id'])
    return history