"""
test_api.py — Quick integration tests for the TuneMorph backend.
Run with: python -m pytest backend/app/test_api.py -v
Requires: httpx, pytest, pytest-asyncio
"""
import io
import struct
import wave
import math
from pathlib import Path

import pytest

try:
    from fastapi.testclient import TestClient
    from backend.app.main import app
    client = TestClient(app)
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


SAMPLE_RATE = 22050


def make_sine_wav(freq: float = 440.0, duration: float = 0.5) -> bytes:
    """Generate a simple sine-wave WAV file in memory."""
    n = int(SAMPLE_RATE * duration)
    samples = [int(16384 * math.sin(2 * math.pi * freq * i / SAMPLE_RATE)) for i in range(n)]
    buf = io.BytesIO()
    with wave.open(buf, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(struct.pack(f"<{n}h", *samples))
    return buf.getvalue()


@pytest.mark.skipif(not HAS_DEPS, reason="FastAPI deps not installed")
def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


@pytest.mark.skipif(not HAS_DEPS, reason="FastAPI deps not installed")
def test_home():
    r = client.get("/")
    assert r.status_code == 200
    assert "TuneMorph" in r.json()["name"]


@pytest.mark.skipif(not HAS_DEPS, reason="FastAPI deps not installed")
def test_analyze_wav():
    wav_bytes = make_sine_wav(freq=261.626, duration=1.0)  # C4
    r = client.post(
        "/analyze",
        files={"file": ("test_c4.wav", io.BytesIO(wav_bytes), "audio/wav")},
        data={"instrument": "piano", "level": "beginner"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "analysis" in data
    notes = data["analysis"]["detected_notes"]
    assert isinstance(notes, list)
    # Every note must carry start_time and be ordered ascending
    for n in notes:
        assert "start_time" in n, f"Missing start_time in note: {n}"
        assert "duration" in n
        assert n["start_time"] >= 0
    times = [n["start_time"] for n in notes]
    assert times == sorted(times), "Notes are not ordered by start_time"


@pytest.mark.skipif(not HAS_DEPS, reason="FastAPI deps not installed")
def test_freq_to_note_helper():
    """freq_to_note must map known piano frequencies to the correct note name."""
    from backend.app.main import freq_to_note
    assert freq_to_note(261.63) == "C4"   # middle C
    assert freq_to_note(440.0)  == "A4"
    assert freq_to_note(329.63) == "E4"
    assert freq_to_note(0) is None         # silence → None
    assert freq_to_note(-1) is None        # invalid → None


@pytest.mark.skipif(not HAS_DEPS, reason="FastAPI deps not installed")
def test_recordings_roundtrip():
    wav_bytes = make_sine_wav()
    # Upload
    r = client.post(
        "/recordings",
        files={"file": ("test.wav", io.BytesIO(wav_bytes), "audio/wav")},
    )
    assert r.status_code == 200
    rec_id = r.json()["id"]

    # List
    r2 = client.get("/recordings")
    assert any(rec["id"] == rec_id for rec in r2.json())

    # Download
    r3 = client.get(f"/recordings/{rec_id}")
    assert r3.status_code == 200

    # Delete
    r4 = client.delete(f"/recordings/{rec_id}")
    assert r4.status_code == 200


@pytest.mark.skipif(not HAS_DEPS, reason="FastAPI deps not installed")
def test_oversized_upload():
    big = b"\x00" * (21 * 1024 * 1024)  # 21 MB
    r = client.post(
        "/analyze",
        files={"file": ("big.wav", io.BytesIO(big), "audio/wav")},
        data={"instrument": "piano", "level": "beginner"},
    )
    assert r.status_code == 413
