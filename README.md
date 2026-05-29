# TuneMorph (private)

Turn any song into something you can play.

## Repo layout
- `backend/` – FastAPI API server
- `frontend/` – UI (scaffold)
- `samples/` – test audio/data

## Backend
### Install & run
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Then open: http://localhost:8000/docs

### API
- `GET /` health check
- `POST /analyze`
  - multipart form: `file` + optional `instrument`, `level`
  - returns placeholder analysis + practice ideas

## Notes
This repo is kept private. Add your API keys via environment variables / `.env` and never commit them.
