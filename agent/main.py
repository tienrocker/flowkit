"""Google Flow Agent — FastAPI entry point."""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from agent.config import API_HOST, API_PORT
from agent.db.schema import init_db
from agent.api.characters import router as characters_router
from agent.api.projects import router as projects_router
from agent.api.videos import router as videos_router
from agent.api.scenes import router as scenes_router
from agent.api.requests import router as requests_router
from agent.worker.processor import process_pending_requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    init_db()
    logger.info("Google Flow Agent starting on %s:%d", API_HOST, API_PORT)

    # Start background worker
    worker_task = asyncio.create_task(process_pending_requests())
    logger.info("Background worker started")

    yield

    worker_task.cancel()
    logger.info("Google Flow Agent stopped")


app = FastAPI(title="Google Flow Agent", version="0.1.0", lifespan=lifespan)
app.include_router(characters_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(videos_router, prefix="/api")
app.include_router(scenes_router, prefix="/api")
app.include_router(requests_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent.main:app", host=API_HOST, port=API_PORT, reload=True)
