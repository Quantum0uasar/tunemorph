# Sample audio files

Drop audio files here to test TuneMorph. Good candidates:

- **Simple melody** — a hummed or whistled tune (best results)
- **Solo piano clip** — a short 3–10 second recording
- **Guitar single string** — plucked individual notes

## Generating a test tone

```bash
# Generates samples/test_cmajor.wav — a clean C major scale
python -m backend.app.generate_test_tone
```

## Recommended test files

| File | Expected notes |
|---|---|
| `test_cmajor.wav` | C4 D4 E4 F4 G4 A4 B4 C5 |
| Any monophonic melody | Detected notes depend on content |

## Tips for best detection accuracy

1. **Quiet background** — background noise confuses pitch detection
2. **Single melody line** — pyin works on one note at a time (monophonic)
3. **WAV or high-bitrate MP3** — compression artifacts can affect pitch accuracy
4. **3–15 seconds** — shorter clips work best for the MVP
