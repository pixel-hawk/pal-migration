from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import uvicorn
import io

from pathlib import Path
import web_service.core as core

app = FastAPI(title="Palworld Save Migrate (Web)")

# Simple template folder
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    content = await file.read()
    try:
        players = core.analyze_zip_bytes(content)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analyze failed: {e}")
    return JSONResponse({"players": players})


@app.post("/migrate")
async def migrate(file: UploadFile = File(...), old_guid: str = Form(...), new_guid: str = Form(...)):
    content = await file.read()
    try:
        out_bytes = core.migrate_zip_bytes(content, old_guid, new_guid)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {e}")
    return StreamingResponse(io.BytesIO(out_bytes), media_type="application/zip", headers={"Content-Disposition": "attachment; filename= migrated.zip"})


if __name__ == "__main__":
    uvicorn.run("web_service.app:app", host="127.0.0.1", port=8000, reload=True)
