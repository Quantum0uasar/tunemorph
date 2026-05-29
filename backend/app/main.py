from pathlib import Path
import shutil
import tempfile
import uuid
from typing import List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel


app = FastAPI(title="TuneMorph AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ephemeral storage for recordings (keeps recordings out of the repo)
RECORDINGS_DIR = Path(tempfile.gettempdir()) / "tunemorph_recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


class RecordingInfo(BaseModel):
    id: str
    filename: str
    size_bytes: int


@app.get("/")
def home():
    return {
        "message": "TuneMorph AI backend is running",
        "tagline": "Turn any song into something you can play.",
    }


@app.post("/analyze")
async def analyze_audio(
    file: UploadFile = File(...),
    instrument: str = Form("guitar"),
    level: str = Form("beginner"),
):
    # TODO: plug your note/tempo detection + model-based lesson generation here.
    return {
        "filename": file.filename,
        "instrument": instrument,
        "level": level,
        "analysis": {
            "detected_notes": ["C", "E", "G"],
            "tempo": "Coming soon",
            "lesson": f"Practice this slowly on {instrument}. Start with one note at a time.",
        },
    }


@app.post("/recordings", response_model=RecordingInfo)
async def upload_recording(file: UploadFile = File(...)):
    rec_id = uuid.uuid4().hex
    sanitized_name = file.filename.replace("/", "_").replace("\\", "_")
    dest = RECORDINGS_DIR / f"{rec_id}_{sanitized_name}"

    with dest.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return RecordingInfo(
        id=rec_id,
        filename=file.filename,
        size_bytes=dest.stat().st_size,
    )


@app.get("/recordings")
def list_recordings() -> List[RecordingInfo]:
    recordings: List[RecordingInfo] = []

    for path in sorted(RECORDINGS_DIR.glob("*")):
        rec_id, _, filename = path.name.partition("_")
        if not rec_id or not filename:
            continue

        recordings.append(
            RecordingInfo(
                id=rec_id,
                filename=filename,
                size_bytes=path.stat().st_size,
            )
        )

    return recordings


@app.get("/recordings/{rec_id}")
def download_recording(rec_id: str):
    for path in RECORDINGS_DIR.glob(f"{rec_id}_*"):
        return FileResponse(path)

    raise HTTPException(status_code=404, detail="Recording not found")
