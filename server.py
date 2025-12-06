from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from scipy.signal import spectrogram
from scipy.ndimage import maximum_filter
from pydub import AudioSegment
import hashlib
import os
import shutil
import psycopg2
from collections import defaultdict

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# database connection
DB_PARAMS = {
    "dbname": "postgres",
    "user": "postgres", 
    "password": "admin123",  # change this later, vulnerable
    "host": "localhost",
    "port": 5432
}

def get_db():
    return psycopg2.connect(**DB_PARAMS)

def init_database():
    conn = get_db()
    cur = conn.cursor()
    
    # songs table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS songs (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255),
            artist VARCHAR(255)
        )
    """)
    
    # fingerprints table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fingerprints (
            id SERIAL PRIMARY KEY,
            song_id INT REFERENCES songs(id) ON DELETE CASCADE,
            hash BIGINT,
            offset_time BIGINT
        )
    """)
    
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hash ON fingerprints(hash)")
    
    conn.commit()
    cur.close()
    conn.close()
    print("db initialized")

def get_fingerprints(filepath):
    print(f"processing {filepath}")
    
    audio = AudioSegment.from_file(filepath)
    audio = audio.set_channels(1).set_frame_rate(44100)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    
    if np.max(np.abs(samples)) > 0:
        samples /= np.max(np.abs(samples))
    
    f, t, Sxx = spectrogram(samples, fs=44100, nperseg=4096, noverlap=2048)
    Sxx = np.log1p(Sxx * 1000)
    
    local_max = maximum_filter(Sxx, size=(20, 20)) == Sxx
    threshold = np.mean(Sxx) * 1.5
    peaks = local_max & (Sxx > threshold)
    
    peak_freqs, peak_times = np.where(peaks)
    peak_list = list(zip(peak_times, peak_freqs))
    peak_list.sort()
    
    print(f"got {len(peak_list)} peaks")
    
    hashes = []
    for i in range(len(peak_list)):
        t1, f1 = peak_list[i]
        
        for j in range(i + 1, min(i + 15, len(peak_list))):
            t2, f2 = peak_list[j]
            t_delta = t2 - t1
            
            if t_delta < 10 or t_delta > 200:
                continue
            
            h_str = f"{f1}|{f2}|{t_delta}"
            h = hashlib.sha1(h_str.encode()).hexdigest()
            h_int = int(h[:16], 16)
            
            if h_int >= 2**63:
                h_int -= 2**64
            
            offset = int(t[t1] * 1000)
            hashes.append((h_int, offset))
    
    print(f"created {len(hashes)} hashes")
    return hashes


def save_song(title, artist, hashes):
    conn = get_db()
    cur = conn.cursor()
    
    # insert song
    cur.execute(
        "INSERT INTO songs (title, artist) VALUES (%s, %s) RETURNING id",
        (title, artist)
    )
    song_id = cur.fetchone()[0]
    
    # insert fingerprints
    for h, offset in hashes:
        cur.execute(
            "INSERT INTO fingerprints (song_id, hash, offset_time) VALUES (%s, %s, %s)",
            (song_id, int(h), int(offset))
        )
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"saved song {song_id}")
    return song_id


def find_match(sample_hashes):
    print(f"matching {len(sample_hashes)} hashes")
    
    conn = get_db()
    cur = conn.cursor()
    
    # get all matching hashes from db
    hash_list = [int(h) for h, _ in sample_hashes]
    cur.execute(
        "SELECT song_id, hash, offset_time FROM fingerprints WHERE hash = ANY(%s)",
        (hash_list,)
    )
    
    matches = cur.fetchall()
    cur.close()
    conn.close()
    
    if not matches:
        print("no matches found")
        return None
    
    print(f"found {len(matches)} matching hashes in db")
    
    # count matches per song - trying time alignment too
    candidates = defaultdict(list)
    sample_dict = {h: offset for h, offset in sample_hashes}
    
    for song_id, h, db_offset in matches:
        if h in sample_dict:
            sample_offset = sample_dict[h]
            time_diff = db_offset - sample_offset
            candidates[song_id].append(time_diff)
    
    if not candidates:
        return None
    
    # find song with most consistent time alignment
    best_song = None
    best_score = 0
    
    for song_id, time_diffs in candidates.items():
        # count how many match around same time offset
        # this is still pretty basic but better than before
        hist = defaultdict(int)
        for td in time_diffs:
            bucket = td // 100  # 100ms buckets
            hist[bucket] += 1
        
        score = max(hist.values())
        print(f"song {song_id}: score {score}")
        
        if score > best_score:
            best_score = score
            best_song = song_id
    
    if best_score < 5:
        return None
    
    return best_song


def get_song_info(song_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT title, artist FROM songs WHERE id = %s", (song_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result


@app.on_event("startup")
def startup():
    init_database()


@app.get("/")
def home():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM songs")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return {"status": "running", "songs": count}


@app.post("/add-song")
async def add_song(file: UploadFile = File(...), title: str = Form(...), artist: str = Form(...)):
    print(f"adding: {title} - {artist}")
    
    path = f"temp_{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    hashes = get_fingerprints(path)
    os.remove(path)
    
    if not hashes:
        return {"error": "couldn't process file"}
    
    song_id = save_song(title, artist, hashes)
    
    return {"id": song_id, "title": title, "artist": artist, "hashes": len(hashes)}


@app.post("/identify")
async def identify(file: UploadFile = File(...)):
    print("identifying...")
    
    path = f"temp_id_{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    hashes = get_fingerprints(path)
    os.remove(path)
    
    if not hashes:
        return {"match": None}
    
    song_id = find_match(hashes)
    
    if not song_id:
        return {"match": None}
    
    info = get_song_info(song_id)
    
    return {
        "match": {
            "id": song_id,
            "title": info[0],
            "artist": info[1]
        }
    }


if __name__ == "__main__":
    import uvicorn
    print("starting server with database support...")
    uvicorn.run(app, host="0.0.0.0", port=8000)