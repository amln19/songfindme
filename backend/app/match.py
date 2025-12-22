from collections import defaultdict
from .database import get_matching_hashes
import logging
import numpy as np

logger = logging.getLogger("shazam")

def match_clip(sample_hashes, return_matches=False, sample_path=None):
    """
    Definitive Matching Algorithm.
    Features:
    1. Inverse Document Frequency (IDF) Weighting (Penalizes common hashes)
    2. Sliding Window Histogram (Aligns time offsets)
    3. Temporal Spread Check (Ensures matches cover the audio clip)
    4. Ratio Test (Confidence check)
    """
    if not sample_hashes:
        return None, []

    # Calculate sample duration from the last hash (approximate)
    sample_duration_ms = 0
    if sample_hashes:
        sample_duration_ms = max(h[1] for h in sample_hashes)

    logger.info(f"Matching {len(sample_hashes)} hashes. Sample Duration: {sample_duration_ms}ms")

    # --- CONSTANTS ---
    BIN_WIDTH = 50       # 50ms tolerance
    MIN_SCORE = 10.0     # Minimum weighted score to consider
    CONFIDENCE_RATIO = 1.6
    
    # Spread Check: Matches must span at least 15% of the sample duration
    # This prevents "burst" matches from noise.
    MIN_SPREAD_RATIO = 0.15 
    # -----------------

    # 1. DB Lookup
    hash_values = [int(h) for h, _ in sample_hashes]
    rows = get_matching_hashes(hash_values)

    if not rows:
        return None, []

    # 2. IDF Calculation
    hash_counts = defaultdict(int)
    for _, h, _ in rows:
        hash_counts[int(h)] += 1
    
    # 3. Candidate Generation
    candidates = defaultdict(list)
    sample_map = defaultdict(list)
    for h, off in sample_hashes:
        sample_map[int(h)].append(int(off))

    for song_id, h, db_off in rows:
        h = int(h)
        song_id = int(song_id)
        
        # Aggressive Stop-word removal
        if hash_counts[h] > 500: # Ignore hashes present in >500 matches
            continue
            
        # IDF Weight
        # We use Log weighting which is standard in information retrieval
        # weight = 1 / log(1 + count)
        weight = 1.0 / np.log1p(hash_counts[h])

        for s_off in sample_map[h]:
            candidates[song_id].append((s_off, int(db_off), weight))

    # 4. Scoring per Song
    final_results = [] # (song_id, score, match_details)

    for song_id, matches in candidates.items():
        if len(matches) < 5: 
            continue

        # -- Step A: Time Alignment Histogram --
        histogram = defaultdict(float)
        # Store matches in bins for easier retrieval later
        bin_matches = defaultdict(list) 

        for s_off, db_off, w in matches:
            delta = db_off - s_off
            bin_idx = int(delta // BIN_WIDTH)
            histogram[bin_idx] += w
            bin_matches[bin_idx].append((s_off, db_off))

        # Smoothing: Sum (bin-1, bin, bin+1)
        max_score = 0
        best_bin = 0
        
        sorted_bins = sorted(histogram.keys())
        for b in sorted_bins:
            # Window score
            score = histogram[b] + histogram.get(b-1, 0) + histogram.get(b+1, 0)
            if score > max_score:
                max_score = score
                best_bin = b
        
        if max_score < MIN_SCORE:
            continue

        # -- Step B: Temporal Spread Check (The "Anti-Noise" Filter) --
        # Retrieve all matches that contributed to the peak
        valid_matches = []
        valid_matches.extend(bin_matches[best_bin])
        valid_matches.extend(bin_matches[best_bin-1])
        valid_matches.extend(bin_matches[best_bin+1])
        
        if not valid_matches:
            continue

        # Calculate time span of the matches in the sample
        sample_offsets = [m[0] for m in valid_matches]
        min_s = min(sample_offsets)
        max_s = max(sample_offsets)
        spread_ms = max_s - min_s
        
        # If matches are too clustered (e.g., all within 200ms), reject.
        # But if the sample itself is super short (1s), we adjust.
        required_spread = max(1000, sample_duration_ms * MIN_SPREAD_RATIO)
        
        if spread_ms < required_spread:
             # Reduce score heavily if spread is bad
            logger.info(f"Song {song_id} rejected: Poor spread ({spread_ms}ms < {required_spread}ms)")
            max_score *= 0.1 

        final_results.append((song_id, max_score, valid_matches))

    # 5. Ranking & Confidence
    final_results.sort(key=lambda x: x[1], reverse=True)

    if not final_results:
        return None, []

    best_song_id, best_score, best_matches = final_results[0]
    
    # Ratio Test
    if len(final_results) > 1:
        second_score = final_results[1][1]
        ratio = best_score / (second_score + 0.00001)
        
        if ratio < CONFIDENCE_RATIO:
            logger.info(f"Ambiguous match: Ratio {ratio:.2f} < {CONFIDENCE_RATIO}")
            return None, []

    logger.info(f"MATCH FOUND: Song {best_song_id} Score: {best_score:.2f}")

    if return_matches:
        # Format for frontend
        details = []
        for s_off, db_off in best_matches:
            details.append({
                "hash": 0,
                "sample_offset_ms": s_off,
                "db_offset_ms": db_off,
                "delta_ms": db_off - s_off
            })
        return best_song_id, details

    return best_song_id, []