"""
generate_test_tone.py
─────────────────────
Utility script: generates a simple multi-note WAV file for testing
the /analyze endpoint without needing a real recording.

Usage:
    python -m backend.app.generate_test_tone
    # Writes samples/test_cmajor.wav
"""
import struct
import wave
import math
from pathlib import Path

SAMPLE_RATE = 22050
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
A4_FREQ = 440.0
A4_MIDI = 69


def note_to_freq(note: str, octave: int) -> float:
    midi = (octave + 1) * 12 + NOTE_NAMES.index(note)
    return A4_FREQ * (2 ** ((midi - A4_MIDI) / 12))


def generate_sine(freq: float, duration: float, sr: int = SAMPLE_RATE) -> list:
    n_samples = int(sr * duration)
    samples = []
    for i in range(n_samples):
        t = i / sr
        # Sine wave with simple envelope
        envelope = min(i / (sr * 0.01), 1.0) * min((n_samples - i) / (sr * 0.05), 1.0)
        sample = int(32767 * envelope * math.sin(2 * math.pi * freq * t))
        samples.append(max(-32768, min(32767, sample)))
    return samples


def write_wav(path: Path, samples: list, sr: int = SAMPLE_RATE):
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)  # 16-bit
        w.setframerate(sr)
        data = struct.pack(f"<{len(samples)}h", *samples)
        w.writeframes(data)


def main():
    out_path = Path("samples/test_cmajor.wav")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # C major scale: C4 D4 E4 F4 G4 A4 B4 C5
    scale = [
        ("C", 4), ("D", 4), ("E", 4), ("F", 4),
        ("G", 4), ("A", 4), ("B", 4), ("C", 5),
    ]
    note_dur = 0.5  # seconds per note
    silence_dur = 0.05  # gap between notes

    all_samples = []
    for note_name, octave in scale:
        freq = note_to_freq(note_name, octave)
        note_samples = generate_sine(freq, note_dur)
        silence = [0] * int(SAMPLE_RATE * silence_dur)
        all_samples.extend(note_samples + silence)

    write_wav(out_path, all_samples)
    print(f"Written: {out_path} ({len(all_samples) / SAMPLE_RATE:.1f}s, {len(scale)} notes)")
    print("Upload this file to /analyze to verify note detection.")


if __name__ == "__main__":
    main()
