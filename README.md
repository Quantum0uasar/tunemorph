# TuneMorph

> **Turn any sound into something you can play.**

TuneMorph listens to any audio — a hummed melody, an uploaded MP3, a recorded riff — and converts it into a visual piano sequence you can watch and learn from. Notes light up on an interactive piano in real time as the detected tune plays back.

---

## Demo

```
Audio in  →  Note detection (pyin + librosa)  →  Piano visualises & plays the notes
```

Record your voice, upload a song snippet, or hum a melody — TuneMorph detects the pitch at each note onset and maps it to the nearest piano key, then animates the keys in sequence so you can follow along and learn the tune.

---

## Features

| Feature | Status |
|---|---|
| Record audio via microphone | ✅ |
| Upload audio (MP3, WAV, OGG, WEBM, M4A) | ✅ |
| Real-time waveform visualiser | ✅ |
| Pitch detection via pyin (librosa) | ✅ |
| Tempo (BPM) estimation | ✅ |
| Key centre detection | ✅ |
| Animated interactive piano (C2–C6) | ✅ |
| Playback with speed control (0.25×–2×) | ✅ |
| Loop mode | ✅ |
| Progress seek bar | ✅ |
| Practice tip generator (beginner/intermediate/advanced) | ✅ |
| Dark / light mode | ✅ |
| Keyboard shortcuts (A–L keys → piano notes) | ✅ |
| Demo/offline mode (works without backend) | ✅ |
| Docker + docker-compose | ✅ |
| Multi-instrument support (guitar, voice, etc.) | 🔜 |
| Export as MIDI file | 🔜 |
| Real-time in-browser pitch detection (no backend) | 🔜 |
| GPT-powered lesson generation | 🔜 |

---

## Architecture

```
tunemorph/
├── frontend/
│   └── index.html          # Vanilla JS + WebAudio API + MediaRecorder
├── backend/
│   └── app/
│       ├── __init__.py
│       └── main.py         # FastAPI + librosa pitch detection
├── samples/                # Test audio files (add your own)
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── .env.example
```

### Backend stack
- **FastAPI** — async REST API
- **librosa** — pitch detection (`pyin` algorithm), onset detection, tempo estimation
- **soundfile / ffmpeg** — audio format conversion (any format → WAV)

### Frontend stack
- Pure HTML/CSS/JS — zero build step, opens directly in browser
- **Web Audio API** — piano synthesis (triangle oscillator + ADSR envelope)
- **MediaRecorder API** — microphone capture
- **Canvas API** — live waveform visualiser

---

## Quick start

### Option A — Python (recommended for development)

**1. Clone**
```bash
git clone https://github.com/Quantum0uasar/tunemorph.git
cd tunemorph
```

**2. Set up Python environment**
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

> **Note:** librosa depends on `libsndfile`. On Ubuntu/Debian: `sudo apt-get install libsndfile1`. On macOS: `brew install libsndfile`. On Windows: installed automatically by soundfile.

**3. Install ffmpeg (optional but recommended)**
```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt-get install ffmpeg

# Windows: download from https://ffmpeg.org/download.html and add to PATH
```

**4. Start the backend**
```bash
uvicorn backend.app.main:app --reload
# → API running at http://localhost:8000
# → Interactive docs at http://localhost:8000/docs
```

**5. Open the frontend**
```bash
# Open frontend/index.html directly in your browser, or:
python -m http.server 3000 --directory frontend
# → http://localhost:3000
```

Or use the Makefile shortcut:
```bash
make install   # set up venv + deps
make dev       # start both backend and frontend
```

---

### Option B — Docker

```bash
docker-compose up --build
# Backend → http://localhost:8000
# Frontend → http://localhost:3000
```

---

## API reference

Interactive docs: `http://localhost:8000/docs`

### `POST /analyze`

Upload audio and get back detected notes.

**Form fields:**
| Field | Type | Default | Description |
|---|---|---|---|
| `file` | file | required | Audio file (MP3, WAV, OGG, WEBM, M4A) |
| `instrument` | string | `"any"` | Hint for lesson tips (`piano`, `guitar`, `voice`, `any`) |
| `level` | string | `"beginner"` | Skill level for practice tip (`beginner`, `intermediate`, `advanced`) |

**Response:**
```json
{
  "filename": "my-melody.mp3",
  "instrument": "piano",
  "level": "beginner",
  "analysis": {
    "detected_notes": [
      { "note": "C4", "duration": 0.42, "freq": 261.63 },
      { "note": "E4", "duration": 0.38, "freq": 329.63 },
      { "note": "G4", "duration": 0.51, "freq": 392.0 }
    ],
    "tempo": 118.5,
    "key_center": "C",
    "duration": 3.2,
    "lesson": "Start with just the first 4 notes and repeat them until they feel natural."
  }
}
```

### `POST /recordings`

Save a recording blob from the browser.

### `GET /recordings`

List all saved recordings.

### `GET /recordings/{id}`

Download a saved recording.

### `DELETE /recordings/{id}`

Delete a recording.

---

## How note detection works

1. **Upload** — audio is received as a multipart upload and saved to a temp file
2. **Convert** — ffmpeg converts the audio to 22050 Hz mono WAV for consistent processing
3. **Load** — librosa loads the WAV into a numpy array
4. **Tempo** — `librosa.beat.beat_track()` estimates BPM
5. **Onset detection** — `librosa.onset.onset_detect()` finds where notes start (attack transients)
6. **Pitch (pyin)** — `librosa.pyin()` runs probabilistic YIN pitch estimation at every frame
7. **Note mapping** — at each onset window, the median voiced frequency is converted to the nearest MIDI note name (e.g. 261 Hz → C4)
8. **Key detection** — pitch class histogram determines the most common root note
9. **Return** — a JSON list of `{note, duration, freq}` events is returned to the frontend

### Offline / demo mode

If the backend is unreachable, the frontend automatically falls back to a demo C major scale so you can still explore the piano UI.

---

## Keyboard shortcuts

| Key | Note |
|---|---|
| A | C4 |
| W | C#4 |
| S | D4 |
| E | D#4 |
| D | E4 |
| F | F4 |
| T | F#4 |
| G | G4 |
| Y | G#4 |
| H | A4 |
| U | A#4 |
| J | B4 |
| K | C5 |

---

## Adding test audio

Drop audio files into the `samples/` directory and upload them via the UI.

Good sources for short melody clips to test with:
- Record yourself humming a tune (cleanest single pitch)
- A solo piano MIDI rendered to WAV
- A whistled melody
- Short monophonic instrument recordings

**Note:** TuneMorph's pyin detector works best on **monophonic** (single-voice) audio. Polyphonic audio (chords, full songs with many instruments) will produce approximate results — chord detection is on the roadmap.

---

## Roadmap

- [ ] **MIDI export** — download the detected sequence as a `.mid` file
- [ ] **In-browser pitch detection** — Crepe.js or WASM port so no backend needed
- [ ] **Chord detection** — identify chords from polyphonic audio
- [ ] **Multi-instrument synthesis** — guitar, violin, synth voices for playback
- [ ] **Score view** — render the detected notes on a simple musical staff
- [ ] **GPT lesson generator** — personalised practice plans via OpenAI API
- [ ] **Mobile PWA** — installable on iOS/Android

---

## License

MIT — see [LICENSE](LICENSE).

Built by [Jaideep Singh](https://github.com/Quantum0uasar) · Western University CS
