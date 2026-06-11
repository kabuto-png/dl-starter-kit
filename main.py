import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from akc.core.config import settings
from akc.patterns.store import JsonlStore

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


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
