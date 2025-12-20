from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil

from fingerprint import fingerprint
from database import init_db, save_song, find_match, get_song_info

app = FastAPI()

# cors for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.on_event("startup")
def startup():
    init_db()
    print("backend ready")


@app.get("/")
def home():
    return {"status": "ok", "message": "audio fingerprinting api"}


@app.post("/add-song")
async def add_song(
    file: UploadFile = File(...), 
    title: str = Form(...), 
    artist: str = Form(...)
):
    print(f"adding: {title} - {artist}")
    
    path = os.path.join(UPLOAD_DIR, file.filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    try:
        hashes, duration = fingerprint(path)
        
        if not hashes:
            return {"error": "no fingerprints generated"}
        
        song_id = save_song(title, artist, int(duration), hashes)
        
        return {
            "message": "song added",
            "song_id": song_id,
            "title": title,
            "artist": artist,
            "fingerprints": len(hashes)
        }
    except Exception as e:
        print(f"error: {e}")
        return {"error": str(e)}
    finally:
        if os.path.exists(path):
            os.remove(path)


@app.post("/identify")
async def identify(file: UploadFile = File(...)):
    print("identifying...")
    
    path = os.path.join(UPLOAD_DIR, f"temp_{file.filename}")
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    try:
        hashes, _ = fingerprint(path)
        
        if not hashes:
            return {
                "match_song_id": None,
                "title": None,
                "artist": None,
                "message": "couldn't process audio"
            }
        
        song_id = find_match(hashes)
        
        if not song_id:
            return {
                "match_song_id": None,
                "title": None,
                "artist": None
            }
        
        info = get_song_info(song_id)
        
        return {
            "match_song_id": song_id,
            "title": info[0],
            "artist": info[1]
        }
    except Exception as e:
        print(f"error: {e}")
        return {"error": str(e)}
    finally:
        if os.path.exists(path):
            os.remove(path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)