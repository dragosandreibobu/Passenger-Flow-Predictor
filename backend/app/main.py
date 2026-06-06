from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from app.api import detect, cameras
from fastapi.responses import JSONResponse
from app.core.config import STATIC_DIR
import os

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/dashboard?v=ai_heatmap_final")

@app.get("/api/health")
def health():
    return JSONResponse({"status": "ok"})

@app.get("/dashboard")
def dashboard():
    dashboard_path = os.path.join(STATIC_DIR, "dashboard", "index.html")
    return FileResponse(dashboard_path)

app.include_router(detect.router, prefix="/api")
app.include_router(cameras.router, prefix="/api")
