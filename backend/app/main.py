from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="TuneMorph AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {
        "message": "TuneMorph AI backend is running",
        "tagline": "Turn any song into something you can play."
    }

@app.post("/analyze")
async def analyze_audio(
    file: UploadFile = File(...),
    instrument: str = Form("guitar"),
    level: str = Form("beginner")
):
    return {
        "filename": file.filename,
        "instrument": instrument,
        "level": level,
        "analysis": {
            "detected_notes": ["C", "E", "G"],
            "tempo": "Coming soon",
            "lesson": f"Practice this slowly on {instrument}. Start with one note at a time."
        }
    }
