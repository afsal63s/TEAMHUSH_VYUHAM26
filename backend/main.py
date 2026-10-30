import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api import courses, learners
from api.auth import require_master
from config import get_settings
from db import repos
from db.connection import close_client, get_client

logger = logging.getLogger("onlynerd")
RESULTS = Path(__file__).resolve().parent / "results" / "results.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not get_settings().MASTER_PASSWORD.get_secret_value():
        logger.warning("MASTER_PASSWORD is empty: every route is open (dev mode)")
    get_client()
    await repos.ensure_indexes()
    if stale := await repos.fail_generating_courses():
        logger.warning("marked %d course(s) stuck in 'generating' as failed", stale)
    if stale := await repos.fail_pending_resources():
        logger.warning("marked %d research job(s) stuck in 'pending' as failed", stale)
    yield
    await close_client()


app = FastAPI(title="OnlyNerd", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["Content-Type", "X-Master-Password"],
)
app.include_router(courses.router)
app.include_router(learners.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/eval/results", dependencies=[Depends(require_master)])
async def eval_results() -> FileResponse:
    if not RESULTS.exists():
        raise HTTPException(404, "no eval results yet")
    return FileResponse(RESULTS, media_type="application/json")
