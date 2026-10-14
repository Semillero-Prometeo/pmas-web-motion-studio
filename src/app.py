from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src import local_sequences

STATIC_DIR = Path(__file__).resolve().parent / "static"
app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/local/sequences")
def list_local_sequences() -> dict[str, Any]:
    return local_sequences.store.list_payload()


@app.get("/local/sequences/{name:path}")
def get_local_sequence(name: str) -> dict[str, Any]:
    try:
        return local_sequences.store.get(name)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/local/sequences")
def save_local_sequence(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("sequence")
    if not isinstance(raw, dict):
        raise HTTPException(status_code=400, detail="Formato de secuencia inválido")
    try:
        return local_sequences.store.save(
            raw, overwrite=bool(payload.get("overwrite", False))
        )
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
