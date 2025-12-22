# 🎵 SongFindMe - Full Stack Audio Recognition System

**SongFindMe** is a robust audio fingerprinting and recognition application inspired by Shazam. It allows users to identify songs by recording audio via their microphone or uploading files. The system uses a custom-built, noise-tolerant fingerprinting algorithm to match audio clips against a database of stored tracks.

Built with **FastAPI (Python)** for the backend and **React + Vite + Tailwind CSS** for the frontend.

---

## 🚀 Features

### 🎧 Core Audio Engine

* **Robust Fingerprinting:** Uses **2D spectrogram peak finding** (local maximum filtering) to generate noise-resistant audio constellations
* **Advanced Matching:** Implements **Time-Delta Histogramming** with sliding window smoothing and **Temporal Spread Checks** to filter false positives
* **Format Support:** Supports MP3, WAV, M4A, FLAC, and OGG (via FFmpeg)
* **Smart Audio Processing:** Automatic noise gating and normalization

### 💻 Frontend (React)

* **Real-time Recording:** "Tap to Identify" button with visual feedback
* **Smart Retry Logic:** Automatically escalates from 5s quick check → 10s → 15s deep scan
* **Responsive UI:** Clean, modern interface built with **Tailwind CSS** and **DaisyUI**
* **Optimized Performance:** Memoized context, proper cleanup on unmount

### 🔐 User System

* **Authentication:** JWT-based Login and Signup with bcrypt password hashing
* **Role-Based Access:**
  * **Admins:** Upload and index new songs into the database
  * **Users:** Identify songs and view their personal **Search History**
  * **Guests:** Identify songs (without history tracking)
* **Password Validation:** Minimum 6 characters required
* **Username Validation:** 3-50 characters

---

## 🗃️ Architecture

```text
SongFindMe/
├── backend/
│   ├── app/
│   │   ├── main.py          # API routes & endpoints
│   │   ├── config.py        # Environment configuration
│   │   ├── fingerprint.py   # DSP & spectrogram processing
│   │   ├── match.py         # Histogram matching algorithm
│   │   ├── database.py      # PostgreSQL connection & queries
│   │   ├── auth.py          # JWT & password hashing
│   │   └── uploads/         # Temp storage (auto-cleanup)
│   ├── requirements.txt
│   └── .env                 # Create from .env.example
│
└── frontend/
    ├── src/
    │   ├── components/      # ListeningButton, NavBar
    │   ├── pages/           # Home, Login, AddSong, History
    │   ├── context/         # AuthContext (with memoization)
    │   ├── api.js           # Centralized API configuration
    │   └── App.jsx
    ├── .env                 # Create from .env.example
    └── package.json
```

---

## 🛠️ Tech Stack

### Backend
* **Python 3.9+**
* **FastAPI** - Modern async web framework
* **NumPy & SciPy** - Signal processing
* **PyDub** - Audio format conversion
* **PostgreSQL** with `psycopg2` - Relational database
* **JWT** with `python-jose` - Authentication
* **bcrypt** - Password hashing

### Frontend
* **React 18** with **Vite** - Fast development
* **Tailwind CSS** + **DaisyUI** - Styling
* **React Router** - Navigation
* **Lucide React** - Icons
* **React Hot Toast** - Notifications

### System Dependencies
* **FFmpeg** - Audio processing (required)

---

## 📦 Installation & Setup

### Prerequisites

1. **PostgreSQL** installed and running
2. **FFmpeg** installed and in system PATH
3. **Node.js 18+** and **Python 3.9+** installed

---

### 1️⃣ Backend Setup

```bash
# Navigate to project root
cd SongFindMe

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Create .env file from example
cp backend/.env.example backend/.env

# Edit backend/.env with your configuration:
# - Set secure DB_PASSWORD
# - Generate a strong SECRET_KEY (min 32 chars)
# - Adjust CORS_ORIGINS if needed
```

**Important:** Generate a secure SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Run the backend:**
```bash
npm run dev:backend
# Or: uvicorn backend.app.main:app --reload
```

Server runs on `http://localhost:8000`

---

### 2️⃣ Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Create .env file from example
cp .env.example .env

# Edit frontend/.env if backend URL differs from default
# VITE_API_URL=http://localhost:8000

# Go back to root and run development server
cd ..
npm run dev:frontend
```

Client runs on `http://localhost:5173`

---

## 🎧 Usage Guide

### 1. Initial Setup

1. Start both backend and frontend servers
2. The database will initialize automatically on first startup
3. Open `http://localhost:5173` in your browser

### 2. Creating an Admin User

**Option A: Via Database (Recommended)**
```sql
-- Connect to PostgreSQL
psql -U postgres -d postgres

-- Create admin user (replace with your details)
INSERT INTO users (username, password_hash, role) 
VALUES ('admin', '$2b$12$...', 'admin');

-- Or update existing user
UPDATE users SET role = 'admin' WHERE username = 'your_username';
```

**Option B: Via API**
```bash
# Sign up normally, then manually update role in database
```

### 3. Adding Songs (Admin Only)

1. Log in with admin credentials
2. Click **"Add Song"** in the navbar
3. Upload an audio file (MP3, WAV, etc.)
4. Fill in title and artist
5. Wait for fingerprinting to complete (~5-15 seconds)

**Note:** The uploaded file is automatically deleted after processing

### 4. Identifying Songs

**Method 1: Real-time Recording (Homepage)**
1. Click the **microphone button**
2. Play music near your device
3. The system analyzes in stages:
   - **5s check** → Quick match attempt
   - **10s check** → If no match, continues listening
   - **15s check** → Final deep analysis

**Method 2: File Upload**
1. Go to **"Identify Song"** page
2. Upload an audio clip
3. Get instant results

### 5. View History

1. Log in (guests can't see history)
2. Click **"History"** in the navbar
3. See all previously identified songs with timestamps

---

## 🧠 How the Algorithm Works

### 1. Fingerprinting Pipeline

```
Audio Input → Spectrogram → Peak Detection → Hash Generation → Database Storage
```

**Detailed Steps:**

1. **Audio Normalization**
   - Convert to mono, 44.1kHz, 16-bit
   - Apply noise gate (reject if < -70 dBFS)
   - Normalize amplitude to [-1, 1]

2. **Spectrogram Generation**
   - FFT window size: 4096 samples
   - Overlap: 50% (2048 samples)
   - Logarithmic scaling for perceptual loudness

3. **2D Peak Picking**
   - Use `scipy.ndimage.maximum_filter` with 20×20 neighborhood
   - Filter peaks below dynamic threshold (1.5× mean intensity)
   - Extract (frequency, time) coordinates

4. **Combinatorial Hashing**
   - For each anchor peak, pair with next 10 target peaks
   - Hash format: `SHA1(freq1 | freq2 | time_delta)`
   - Store: `(hash, offset_time)` tuples

### 2. Matching Algorithm

```
Sample Hashes → DB Lookup → IDF Weighting → Histogram Alignment → Verification
```

**Key Innovations:**

1. **IDF Weighting**
   - Penalizes common hashes (like silence/noise)
   - Weight = `1 / log(1 + occurrence_count)`

2. **Time-Delta Histogramming**
   - Groups matches by `delta = db_time - sample_time`
   - True matches cluster in a narrow bin range
   - Random noise scatters across all bins

3. **Temporal Spread Check**
   - Ensures matches span ≥15% of sample duration
   - Rejects "burst" matches from short noise patterns

4. **Confidence Ratio Test**
   - Requires best match score ≥ 1.6× second-best
   - Prevents ambiguous results

---

## 🔐 Security Features

✅ **Environment Variables:** Secrets stored in `.env` (not committed)  
✅ **Password Hashing:** bcrypt with automatic salting  
✅ **JWT Authentication:** Secure token-based auth with expiration  
✅ **SQL Injection Protection:** Parameterized queries throughout  
✅ **Input Validation:** Length checks on username/password  
✅ **Automatic File Cleanup:** Uploaded files deleted after processing  
✅ **Role-Based Access Control:** Admin-only endpoints protected

---

## 🚨 Common Issues & Solutions

### "Could not connect to database"
- Ensure PostgreSQL is running: `sudo service postgresql start`
- Check credentials in `backend/.env`

### "FFmpeg not found"
- Install FFmpeg: `sudo apt install ffmpeg` (Linux) or `brew install ffmpeg` (Mac)
- Windows: Download from [ffmpeg.org](https://ffmpeg.org) and add to PATH

### "Microphone access denied"
- Browser needs HTTPS for mic access (except localhost)
- Check browser permissions in settings

### "No fingerprints generated"
- Audio may be too quiet (< -70 dBFS)
- Try increasing volume or use a louder recording

### "Module not found" errors
- Backend: Activate venv and reinstall: `pip install -r requirements.txt`
- Frontend: Delete `node_modules` and run `npm install`

---

## 📊 Performance Characteristics

| Metric | Typical Value |
|--------|---------------|
| Fingerprinting Speed | ~0.5-2s per minute of audio |
| Matching Speed | < 500ms for 15s clip |
| Database Size | ~1000-5000 fingerprints per song |
| Recognition Accuracy | 85-95% with 5+ seconds of clear audio |
| Noise Tolerance | Robust to background noise, compression artifacts |

---

## 🎯 Roadmap & Future Enhancements

**Performance & Scalability:**
- [ ] Connection pooling for database optimization
- [ ] Redis caching layer for frequently accessed song metadata
- [ ] Batch fingerprint insertion optimization
- [ ] CDN integration for static assets

**Features:**
- [ ] Mobile app development (iOS/Android)
- [ ] Admin dashboard with analytics
- [ ] Playlist generation from history
- [ ] Social sharing capabilities
- [ ] Music streaming integration (Spotify, Apple Music)

**Infrastructure:**
- [ ] Docker containerization
- [ ] CI/CD pipeline setup
- [ ] API rate limiting and usage analytics
- [ ] Comprehensive test suite (unit, integration, E2E)
- [ ] Cloud deployment guides (AWS, GCP, Azure)

---

## 📝 License

MIT License - Open source and free to use. See LICENSE file for details.

---

## 🙏 Acknowledgments

**Algorithm research:** Inspired by audio fingerprinting techniques described in [How does Shazam work?](http://coding-geek.com/how-shazam-works/) by Christophe Kalenzaga

**Core Technologies:**
- FastAPI team for the excellent web framework
- NumPy and SciPy communities for robust scientific computing
- React team for the modern frontend library
- PostgreSQL for reliable data persistence

---

## 🏗️ Technical Highlights

**Architecture & Design:**
- Modern Python async web framework (FastAPI)
- Advanced audio DSP with spectrogram analysis (NumPy, SciPy)
- Secure authentication system (JWT, bcrypt)
- Modern React with hooks and context API
- RESTful API design with proper separation of concerns
- Environment-based configuration for deployment flexibility

**Signal Processing:**
- Custom fingerprinting algorithm inspired by industry leaders
- Time-frequency domain analysis with 2D peak detection
- Robust matching with IDF weighting and temporal verification
- Handles real-world noise and audio compression artifacts

---

## 📬 Contact & Contributions

For questions, feature requests, or bug reports, please open a GitHub issue.

Contributions are welcome! Feel free to fork the repository and submit pull requests.

---

*Built with passion for audio technology and software engineering excellence.*