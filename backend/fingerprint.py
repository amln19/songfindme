import numpy as np
from scipy.signal import spectrogram
from scipy.ndimage import maximum_filter
from pydub import AudioSegment
import hashlib

def fingerprint(file_path):
    """extract fingerprints from audio file"""
    print(f"processing: {file_path}")
    
    # load and normalize audio
    try:
        audio = AudioSegment.from_file(file_path)
        audio = audio.set_channels(1).set_frame_rate(44100).set_sample_width(2)
        
        # check if it's too quiet
        if audio.dBFS < -70:
            print("audio too quiet")
            return [], 0.0
        
        samples = np.array(audio.get_array_of_samples()).astype(np.float32)
        
        if np.max(np.abs(samples)) > 0:
            samples /= np.max(np.abs(samples))
            
    except Exception as e:
        print(f"error loading audio: {e}")
        return [], 0.0
    
    duration = len(samples) / 44100.0
    
    # generate spectrogram
    f, t, Sxx = spectrogram(
        samples,
        fs=44100,
        window='hann',
        nperseg=4096,
        noverlap=2048
    )
    
    # log scaling
    Sxx = np.log1p(Sxx * 1000)
    
    # find peaks using 2d max filter
    PEAK_SIZE = (20, 20)
    local_max = maximum_filter(Sxx, size=PEAK_SIZE) == Sxx
    
    threshold = np.mean(Sxx) * 1.5
    peaks = local_max & (Sxx > threshold)
    
    peak_freqs, peak_times = np.where(peaks)
    peak_list = list(zip(peak_times, peak_freqs))
    peak_list.sort()
    
    print(f"found {len(peak_list)} peaks")
    
    # create hashes by pairing peaks
    hashes = []
    FAN_VALUE = 10
    MIN_TIME_DELTA = 0
    MAX_TIME_DELTA = 200
    
    for i in range(len(peak_list)):
        t1, f1 = peak_list[i]
        
        # pair with next few peaks
        for j in range(i + 1, min(i + FAN_VALUE + 50, len(peak_list))):
            t2, f2 = peak_list[j]
            t_delta = t2 - t1
            
            if t_delta < MIN_TIME_DELTA:
                continue
            if t_delta > MAX_TIME_DELTA:
                break
            
            # hash format: freq1 | freq2 | time_delta
            h_str = f"{f1}|{f2}|{t_delta}"
            h = hashlib.sha1(h_str.encode("utf-8")).hexdigest()
            
            # convert to 64-bit int
            h_int = int(h[:16], 16)
            if h_int >= 2**63:
                h_int -= 2**64
            
            offset_ms = int(t[t1] * 1000)
            hashes.append((h_int, offset_ms))
            
            if len(hashes) > 20000:  # safety limit
                break
    
    print(f"generated {len(hashes)} hashes")
    return hashes, duration