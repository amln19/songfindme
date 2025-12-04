from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from scipy.signal import spectrogram
from scipy.ndimage import maximum_filter
from pydub import AudioSegment
import hashlib
import os
import shutil

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# just storing in memory for now, will add db later
songs = {}
next_id = 1

def get_fingerprints(filepath):
    print(f"processing {filepath}")
    
    audio = AudioSegment.from_file(filepath)
    audio = audio.set_channels(1).set_frame_rate(44100)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    
    if np.max(np.abs(samples)) > 0:
        samples /= np.max(np.abs(samples))
    
    # make spectrogram
    f, t, Sxx = spectrogram(samples, fs=44100, nperseg=4096, noverlap=2048)
    Sxx = np.log1p(Sxx * 1000)
    
    # find peaks
    local_max = maximum_filter(Sxx, size=(20, 20)) == Sxx
    threshold = np.mean(Sxx) * 1.5
    peaks = local_max & (Sxx > threshold)
    
    peak_freqs, peak_times = np.where(peaks)
    peak_list = list(zip(peak_times, peak_freqs))
    peak_list.sort()
    
    print(f"got {len(peak_list)} peaks")
    
    # make hashes
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


def find_match(sample_hashes):
    print(f"trying to match {len(sample_hashes)} hashes")
    
    if not songs:
        print("no songs in db yet")
        return None
    
    matches = {}
    sample_set = set(h for h, _ in sample_hashes)
    
    for song_id, data in songs.items():
        db_set = set(h for h, _ in data["hashes"])
        common = sample_set & db_set
        matches[song_id] = len(common)
        print(f"song {song_id}: {len(common)} matches")
    
    if not matches:
        return None
    
    best = max(matches, key=matches.get)
    count = matches[best]
    
    print(f"best: {best} ({count} matches)")
    
    if count < 5:
        return None
    
    return best


@app.get("/")
def home():
    return {"status": "running", "songs": len(songs)}


@app.post("/add-song")
async def add_song(file: UploadFile = File(...), title: str = "", artist: str = ""):
    global next_id
    
    print(f"adding: {title} - {artist}")
    
    path = f"temp_{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    hashes = get_fingerprints(path)
    os.remove(path)
    
    if not hashes:
        return {"error": "couldn't process file"}
    
    songs[next_id] = {
        "title": title or "unknown",
        "artist": artist or "unknown",
        "hashes": hashes
    }
    
    result = {"id": next_id, "title": title, "hashes": len(hashes)}
    next_id += 1
    return result


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
    
    return {
        "match": {
            "id": song_id,
            "title": songs[song_id]["title"],
            "artist": songs[song_id]["artist"]
        }
    }


if __name__ == "__main__":
    import uvicorn
    print("starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)