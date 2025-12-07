import psycopg2
from psycopg2.extras import execute_values
from collections import defaultdict

# TODO: move these to config file
DB_PARAMS = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "admin123",
    "host": "localhost",
    "port": 5432
}

def get_db():
    return psycopg2.connect(**DB_PARAMS)


def init_db():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS songs (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            artist VARCHAR(255),
            duration_seconds INT
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fingerprints (
            id SERIAL PRIMARY KEY,
            song_id INT NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
            hash BIGINT NOT NULL,
            offset_time BIGINT NOT NULL
        )
    """)
    
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fingerprint_hash ON fingerprints(hash)")
    
    conn.commit()
    cur.close()
    conn.close()
    print("database ready")


def save_song(title, artist, duration, hashes):
    """save song and all its fingerprints"""
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # insert song
        cur.execute(
            "INSERT INTO songs (title, artist, duration_seconds) VALUES (%s, %s, %s) RETURNING id",
            (title, artist, duration)
        )
        song_id = cur.fetchone()[0]
        
        # insert fingerprints in batch
        records = [(song_id, int(h), int(o)) for h, o in hashes]
        execute_values(
            cur,
            "INSERT INTO fingerprints (song_id, hash, offset_time) VALUES %s",
            records
        )
        
        conn.commit()
        print(f"saved song {song_id} with {len(hashes)} fingerprints")
        return song_id
        
    except Exception as e:
        conn.rollback()
        print(f"error saving song: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def find_match(sample_hashes):
    """find best matching song"""
    print(f"matching {len(sample_hashes)} hashes")
    
    conn = get_db()
    cur = conn.cursor()
    
    hash_list = [int(h) for h, _ in sample_hashes]
    cur.execute(
        "SELECT song_id, hash, offset_time FROM fingerprints WHERE hash = ANY(%s)",
        (hash_list,)
    )
    
    matches = cur.fetchall()
    cur.close()
    conn.close()
    
    if not matches:
        return None
    
    print(f"found {len(matches)} hash matches in db")
    
    # build lookup dict for sample hashes
    sample_dict = {h: offset for h, offset in sample_hashes}
    
    # group by song and calculate time deltas
    candidates = defaultdict(list)
    for song_id, h, db_offset in matches:
        if h in sample_dict:
            sample_offset = sample_dict[h]
            time_delta = db_offset - sample_offset
            candidates[song_id].append(time_delta)
    
    if not candidates:
        return None
    
    # find song with best alignment
    best_song = None
    best_score = 0
    
    for song_id, deltas in candidates.items():
        # histogram of time deltas (50ms bins)
        hist = defaultdict(int)
        for delta in deltas:
            bin_idx = delta // 50
            hist[bin_idx] += 1
        
        # best bin is the score
        score = max(hist.values())
        print(f"song {song_id}: {score} aligned matches")
        
        if score > best_score:
            best_score = score
            best_song = song_id
    
    # need at least 10 aligned matches to be confident
    if best_score < 10:
        return None
    
    return best_song


def get_song_info(song_id):
    """get song title and artist"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT title, artist FROM songs WHERE id = %s", (song_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result