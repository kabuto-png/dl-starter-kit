import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import BackgroundTasks, FastAPI

from akc.core.config import settings
from akc.patterns.store import JsonlStore
from akc.remember.distiller import distill_and_store
from akc.remember.models import DistillRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("akc")

store = JsonlStore(kb_dir=settings.akc_kb_dir)


@asynccontextmanager
async def lifespan(app: FastAPI):
    stats = await store.load_stats()
    logger.info(
        "AKC starting — KB_DIR: %s, patterns: %d",
        settings.akc_kb_dir,
        stats["total"],
    )
    yield
    logger.info("AKC shutting down")


app = FastAPI(
    title="AKC — Agent Knowledge Collective",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    stats = await store.load_stats()
    return {"status": "ok", "pattern_count": stats["total"]}


@app.post("/remember", status_code=202)
async def remember(request: DistillRequest, background_tasks: BackgroundTasks):
    """RMB-01: Return 202 immediately; Qwen distillation runs in BackgroundTask.

    The caller is never blocked by LLM latency. distill_and_store handles all
    distillation, deduplication, storage, and confidence feedback asynchronously.
    """
    background_tasks.add_task(distill_and_store, request, store)
    return {}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
