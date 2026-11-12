import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import router as schedule_router

app = FastAPI(
    title="University Department Timetable Solver Microservice",
    description="High-performance automated timetabling engine powered by Timefold Solver, FastAPI and USPU schedule parser.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(schedule_router)

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
@app.get("/ui")
def serve_ui():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "UI not found, please check app/static/index.html"}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "vuz-timetable-solver",
        "engine": "Timefold Solver (Python 3.12)",
        "features": ["2-week-cycle", "atomic-groups", "pinned-lessons", "uspu-parser", "web-ui"],
    }
