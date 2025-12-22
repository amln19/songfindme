import numpy as np
from scipy.signal import spectrogram
from scipy.ndimage import maximum_filter
from pydub import AudioSegment
import hashlib
import logging

logger = logging.getLogger("shazam")

def fingerprint(file_path):
    """
    Generates audio fingerprints using 2D local maximum filtering (Constellation Map).
    This reduces noise sensitivity significantly compared to 1D slice processing.
    """
    logger.info(f"Processing file: {file_path}")

    # 1. Load Audio & Normalize
    try:
        audio = AudioSegment.from_file(file_path)
        
        # Standardize: Mono, 44.1kHz, 16-bit
        audio = audio.set_channels(1).set_frame_rate(44100).set_sample_width(2)
        
        # Noise Gate: If audio is mostly silence, abort early
        if audio.dBFS < -70:
            logger.info("Audio is near silence. Skipping.")
            return [], 0.0

        samples = np.array(audio.get_array_of_samples()).astype(np.float32)
        
        # Normalize to [-1, 1]
        if np.max(np.abs(samples)) > 0:
            samples /= np.max(np.abs(samples))
            
    except Exception as e:
        logger.error(f"Error loading audio: {e}")
        return [], 0.0

    duration = len(samples) / 44100.0
    
    # 2. Generate Spectrogram
    # nperseg=4096 gives good frequency resolution for accurate binning
    f, t, Sxx = spectrogram(
        samples, 
        fs=44100, 
        window='hann', 
        nperseg=4096, 
        noverlap=2048
    )

    # 3. Logarithmic Scaling (Perceptual Loudness)
    # Using log-magnitude makes the system robust to volume changes
    Sxx = np.log1p(Sxx * 1000) # Multiply by 1000 to bring weak signals up before log

    # 4. 2D Local Maximum Filtering (The "Shazam" Peak Picker)
    # We look for points that are the maximum value in their neighborhood.
    # neighborhood_size: (frequency_bins, time_frames)
    # (20, 20) ensures peaks are well separated.
    PEAK_NEIGHBORHOOD_SIZE = (20, 20)
    
    # Find local max
    local_max = maximum_filter(Sxx, size=PEAK_NEIGHBORHOOD_SIZE) == Sxx
    
    # Background threshold: ignore peaks that are just "slightly" louder than silence
    # We use a dynamic threshold based on the global average of the spectrogram
    background_threshold = np.mean(Sxx) * 1.5
    
    # Boolean mask of valid peaks
    detected_peaks = local_max & (Sxx > background_threshold)
    
    # Extract peak coordinates (frequency_bin, time_frame)
    # Note: np.where returns (row_indices, col_indices) -> (freq, time)
    peak_freqs, peak_times = np.where(detected_peaks)
    
    # Sort peaks by time
    peaks = list(zip(peak_times, peak_freqs))
    peaks.sort() # Sort by time

    logger.info(f"Found {len(peaks)} spectral peaks in {duration:.2f}s")

    # 5. Combinatorial Hashing (Anchor-Target Pairing)
    # This creates the unique fingerprints
    hashes = []
    
    FAN_VALUE = 10         # Max pairs per anchor
    MIN_HASH_TIME_DELTA = 0
    MAX_HASH_TIME_DELTA = 200  # ~2 seconds window (spectrogram frames)
    
    # Loop over anchors
    for i in range(len(peaks)):
        t1, f1 = peaks[i]
        
        # Iterate over next few peaks (targets)
        for j in range(i + 1, min(i + FAN_VALUE + 50, len(peaks))):
            t2, f2 = peaks[j]
            t_delta = t2 - t1
            
            if t_delta < MIN_HASH_TIME_DELTA:
                continue
            if t_delta > MAX_HASH_TIME_DELTA:
                break
            
            # Generate Hash: freq1 | freq2 | time_delta
            # This combination is translation-invariant in time
            h_str = f"{f1}|{f2}|{t_delta}"
            h = hashlib.sha1(h_str.encode("utf-8")).hexdigest()
            
            # Truncate to 64-bit integer
            h_int = int(h[:16], 16)
            if h_int >= 2**63: 
                h_int -= 2**64
                
            # Convert time frame to milliseconds
            # t vector from spectrogram is time in seconds. 
            # We can approximate frame -> ms: t[t1] * 1000
            offset_ms = int(t[t1] * 1000)
            
            hashes.append((h_int, offset_ms))
            
            # Limit fan-out
            if len(hashes) > 20000: # Safety break for huge files
                break
    
    return hashes, duration