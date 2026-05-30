"""
TuneMorph AI — FastAPI backend
Converts uploaded audio into piano notes using librosa pitch detection.
"""
from __future__ import annotations

import io
import os
import shutil
import tempfile
import uuid
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

import numpy as np

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Optional heavy deps — gracefully degrade if not installed
try:
    import librosa
    import librosa.display
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logging.warning("librosa not installed — pitch detection will use fallback stub")

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

# ─── App setup ─────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tunemorph")

app = FastAPI(
    title="TuneMorph AI",
    description="Turn any audio into piano notes. Upload or record audio and get back a playable note sequence.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RECORDINGS_DIR = Path(tempfile.gettempdir()) / "tunemorph_recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

# ─── Note / Music utilities ────────────────────────────────────────────────────

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
A4_FREQ = 440.0
A4_MIDI = 69


def freq_to_note(freq: float) -> Optional[str]:
    """Convert a frequency in Hz to the nearest note name (e.g. 'A4')."""
    if freq <= 0:
        return None
    midi = 12 * np.log2(freq / A4_FREQ) + A4_MIDI
    midi_rounded = int(round(midi))
    if midi_rounded < 21 or midi_rounded > 108:  # Piano range
        return None
    octave = (midi_rounded // 12) - 1
    name = NOTE_NAMES[midi_rounded % 12]
    return f"{name}{octave}"


def midi_to_note(midi: int) -> str:
    octave = (midi // 12) - 1
    name = NOTE_NAMES[midi % 12]
    return f"{name}{octave}"


def estimate_key_center(notes: List[str]) -> str:
    """Rough key detection by counting pitch-class occurrences."""
    if not notes:
        return "—"
    count: Dict[str, int] = {n: 0 for n in NOTE_NAMES}
    for n in notes:
        # Strip octave
        pc = n.rstrip("0123456789")
        if pc in count:
            count[pc] += 1
    return max(count, key=count.get)  # most common pitch class


# Krumhansl-Schmuckler key profiles (simplified)
MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]


def lesson_tip(notes: List[str], instrument: str, level: str) -> str:
    count = len(notes)
    tips_by_level = {
        "beginner": [
            f"Start with just the first 4 notes and repeat them until they feel natural.",
            f"Place your right hand thumb on the first key and let your fingers fall on the next ones.",
            f"Play each note slowly — accuracy matters more than speed at this stage.",
        ],
        "intermediate": [
            f"Try to maintain a steady rhythm. Use a metronome set to 60 BPM to start.",
            f"Notice the key signature — most notes cluster around {estimate_key_center(notes)} major.",
            f"Connect each note smoothly with legato technique.",
        ],
        "advanced": [
            f"Look for patterns — this melody has {count} notes total. Identify repeating motifs.",
            f"Explore dynamics: play the first pass soft, the second pass with more expression.",
            f"Transpose this melody up a fifth and see how it sounds in a new key.",
        ],
    }
    tips = tips_by_level.get(level, tips_by_level["beginner"])
    # Pick tip based on note count
    return tips[count % len(tips)]


# ─── Audio processing ──────────────────────────────────────────────────────────

def save_upload_to_temp(file: UploadFile) -> Path:
    """Save uploaded file to a temp path and return it."""
    suffix = Path(file.filename or "audio").suffix or ".webm"
    tmp = Path(tempfile.mktemp(suffix=suffix))
    with tmp.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return tmp


def convert_to_wav(src: Path) -> Path:
    """Convert any audio format to WAV using ffmpeg (if available)."""
    out = src.with_suffix(".wav")
    ret = os.system(f'ffmpeg -y -i "{src}" -ar 22050 -ac 1 "{out}" -loglevel error 2>/dev/null')
    if ret != 0 or not out.exists():
        # ffmpeg not available or failed — return original and hope librosa can read it
        return src
    return out


def detect_notes_librosa(wav_path: Path) -> Dict[str, Any]:
    """
    Use librosa to:
    1. Load audio
    2. Estimate tempo
    3. Detect onsets (note start times)
    4. Extract pitch via pyin at each onset
    5. Return note list with durations
    """
    y, sr = librosa.load(str(wav_path), sr=22050, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    # Tempo estimation
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo_val = float(tempo) if np.isscalar(tempo) else float(tempo[0]) if len(tempo) > 0 else 120.0

    # Onset detection
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units="frames", backtrack=True)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    # Pitch detection (pyin — probabilistic YIN)
    # Works better than basic autocorrelation for melodic content
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"),
        sr=sr,
        frame_length=2048,
        hop_length=512,
    )

    # Map onset times to nearest f0 frame
    hop_length = 512
    notes_out = []
    for i, onset_t in enumerate(onset_times):
        # Next onset or end of file
        next_t = onset_times[i + 1] if i + 1 < len(onset_times) else duration
        note_dur = float(next_t - onset_t)

        # Get the most common voiced pitch within this segment
        start_frame = int(onset_t * sr / hop_length)
        end_frame = int(next_t * sr / hop_length)
        segment_f0 = f0[start_frame:end_frame]
        segment_voiced = voiced_flag[start_frame:end_frame]
        valid_freqs = segment_f0[segment_voiced & (segment_f0 > 0)]

        if len(valid_freqs) == 0:
            continue

        # Use median frequency to reduce noise
        median_freq = float(np.median(valid_freqs))
        note_name = freq_to_note(median_freq)
        if note_name is None:
            continue

        notes_out.append({"note": note_name, "duration": round(note_dur, 3), "freq": round(median_freq, 2)})

    # Cap at 64 notes for playback UX
    notes_out = notes_out[:64]

    note_names_only = [n["note"] for n in notes_out]
    key_center = estimate_key_center(note_names_only)

    return {
        "detected_notes": notes_out,
        "tempo": round(tempo_val, 1),
        "key_center": key_center,
        "duration": round(duration, 2),
    }


def detect_notes_stub(filename: str) -> Dict[str, Any]:
    """
    Fallback stub when librosa isn't available.
    Returns a C major scale as a demo response.
    """
    scale = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"]
    notes = [{"note": n, "duration": 0.5, "freq": 0.0} for n in scale]
    return {
        "detected_notes": notes,
        "tempo": 120.0,
        "key_center": "C",
        "duration": 4.0,
        "_stub": True,
        "_message": "librosa not installed — returning demo scale. Run: pip install librosa",
    }


# ─── Pydantic models ───────────────────────────────────────────────────────────

class NoteEvent(BaseModel):
    note: str
    duration: float
    freq: Optional[float] = None


class AnalysisResult(BaseModel):
    detected_notes: List[NoteEvent]
    tempo: Optional[float] = None
    key_center: Optional[str] = None
    duration: Optional[float] = None
    lesson: Optional[str] = None


class AnalysisResponse(BaseModel):
    filename: str
    instrument: str
    level: str
    analysis: AnalysisResult


class RecordingInfo(BaseModel):
    id: str
    filename: str
    size_bytes: int


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def home():
    return {
        "name": "TuneMorph AI",
        "version": "0.2.0",
        "tagline": "Turn any song into something you can play.",
        "status": "running",
        "librosa_available": LIBROSA_AVAILABLE,
        "endpoints": {
            "analyze": "POST /analyze — upload audio, get back note events",
            "recordings": "POST /recordings — save a recording; GET /recordings — list",
        },
    }


@app.get("/health", tags=["Health"])
def health():
    return {"ok": True, "librosa": LIBROSA_AVAILABLE}


@app.post("/analyze", response_model=AnalysisResponse, tags=["Analysis"])
async def analyze_audio(
    file: UploadFile = File(..., description="Audio file (MP3, WAV, OGG, WEBM, M4A)"),
    instrument: str = Form("any", description="Target instrument hint"),
    level: str = Form("beginner", description="User skill level: beginner | intermediate | advanced"),
):
    """
    Upload an audio file and receive a sequence of detected piano notes with timing.

    - **file**: Any common audio format (WAV, MP3, OGG, WEBM, M4A).
    - **instrument**: Hint for lesson generation (piano, guitar, voice, any).
    - **level**: Skill level for practice tips.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Validate file size (20 MB limit)
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large — max 20 MB")

    # Re-wrap as file-like for further processing
    file.file = io.BytesIO(content)

    tmp_path = None
    wav_path = None
    try:
        tmp_path = save_upload_to_temp(file)
        logger.info(f"Processing: {file.filename} ({len(content)} bytes)")

        if LIBROSA_AVAILABLE:
            # Convert to WAV for reliable librosa loading
            wav_path = convert_to_wav(tmp_path)
            analysis_raw = detect_notes_librosa(wav_path)
        else:
            analysis_raw = detect_notes_stub(file.filename)

        note_events = [NoteEvent(**n) for n in analysis_raw["detected_notes"]]
        lesson = lesson_tip([e.note for e in note_events], instrument, level)

        result = AnalysisResult(
            detected_notes=note_events,
            tempo=analysis_raw.get("tempo"),
            key_center=analysis_raw.get("key_center"),
            duration=analysis_raw.get("duration"),
            lesson=lesson,
        )

        logger.info(f"Detected {len(note_events)} notes in {file.filename}")

        return AnalysisResponse(
            filename=file.filename,
            instrument=instrument,
            level=level,
            analysis=result,
        )

    except Exception as exc:
        logger.error(f"Analysis error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(exc)}")
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        if wav_path and wav_path != tmp_path and wav_path.exists():
            wav_path.unlink(missing_ok=True)


@app.post("/recordings", response_model=RecordingInfo, tags=["Recordings"])
async def upload_recording(file: UploadFile = File(...)):
    """Save a browser recording blob to disk for later download."""
    rec_id = uuid.uuid4().hex
    sanitized = (file.filename or "recording.webm").replace("/", "_").replace("\\", "_")
    dest = RECORDINGS_DIR / f"{rec_id}_{sanitized}"

    with dest.open("wb") as buf:
        shutil.copyfileobj(file.file, buf)

    return RecordingInfo(id=rec_id, filename=sanitized, size_bytes=dest.stat().st_size)


@app.get("/recordings", response_model=List[RecordingInfo], tags=["Recordings"])
def list_recordings():
    """List all saved recordings."""
    out = []
    for path in sorted(RECORDINGS_DIR.glob("*")):
        rec_id, _, fn = path.name.partition("_")
        if rec_id and fn:
            out.append(RecordingInfo(id=rec_id, filename=fn, size_bytes=path.stat().st_size))
    return out


@app.get("/recordings/{rec_id}", tags=["Recordings"])
def download_recording(rec_id: str):
    """Download a saved recording by ID."""
    for path in RECORDINGS_DIR.glob(f"{rec_id}_*"):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Recording not found")


@app.delete("/recordings/{rec_id}", tags=["Recordings"])
def delete_recording(rec_id: str):
    """Delete a saved recording."""
    for path in RECORDINGS_DIR.glob(f"{rec_id}_*"):
        path.unlink()
        return {"deleted": rec_id}
    raise HTTPException(status_code=404, detail="Recording not found")
