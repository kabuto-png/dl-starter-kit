import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()  # populate os.environ so GreenNode SDK can read GREENNODE_CLIENT_ID/SECRET

import uvicorn
from fastapi import BackgroundTasks, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from akc.core.config import settings
from akc.patterns.store import JsonlStore
from akc.remember.distiller import distill_and_store
from akc.remember.models import DistillRequest

import akc.recall.router as recall_router_module
import akc.stats.router as stats_router_module
import akc.export.router as export_router_module
from akc.recall.service import RecallService
from akc.stats.service import StatsService
from akc.export.service import ExportService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("akc")

store = JsonlStore(kb_dir=settings.akc_kb_dir)

# Phase 3: Read path services
recall_svc = RecallService(store=store, memory_id=settings.memory_id)
stats_svc = StatsService(store=store)
export_svc = ExportService(store=store)

# Inject services into routers BEFORE include_router
recall_router_module.recall_service = recall_svc
stats_router_module.stats_service = stats_svc
export_router_module.export_service = export_svc


async def _seed_memory_service():
    """Sync all local patterns to GreenNode Memory Service on startup. Best-effort.

    H4: _sync_pattern_to_memory swallows its own exceptions, so we cannot know
    actual success count without an additional sentinel. Log clearly that this
    is an ATTEMPT count, not confirmed success.
    """
    from akc.remember.distiller import _sync_pattern_to_memory
    from akc.patterns.models import Pattern
    try:
        patterns = await store.load_active(min_tier="experimental", tags=None)
        if not patterns:
            return
        attempted = 0
        for p in patterns:
            try:
                pattern = Pattern(**p)
                await _sync_pattern_to_memory(pattern)
                attempted += 1
            except Exception as inner:
                logger.warning(
                    "Seed pattern %s failed at Pattern construction: %s",
                    p.get("id", "?"), inner,
                )
        logger.info(
            "Memory Service seed attempted for %d/%d patterns "
            "(actual sync success not tracked — check Memory Service warnings)",
            attempted, len(patterns),
        )
    except Exception as exc:
        logger.warning("Memory Service seed failed (non-fatal): %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    stats = await store.load_stats()
    logger.info(
        "AKC starting — KB_DIR: %s, patterns: %d",
        settings.akc_kb_dir,
        stats["total_patterns"],
    )
    await _seed_memory_service()
    yield
    logger.info("AKC shutting down")


app = FastAPI(
    title="AKC — Agent Knowledge Collective",
    version="0.1.0",
    lifespan=lifespan,
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """RCL-06: Wrap FastAPI 422 validation errors in structured format."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Request validation failed",
            "code": "validation_error",
        },
    )


@app.get("/health")
async def health():
    stats = await store.load_stats()
    return {"status": "ok", "pattern_count": stats["total_patterns"]}


@app.post("/remember", status_code=202)
async def remember(request: DistillRequest, background_tasks: BackgroundTasks):
    """RMB-01: Return 202 immediately; Qwen distillation runs in BackgroundTask.

    The caller is never blocked by LLM latency. distill_and_store handles all
    distillation, deduplication, storage, and confidence feedback asynchronously.
    """
    background_tasks.add_task(distill_and_store, request, store)
    return {}


app.include_router(recall_router_module.router)
app.include_router(stats_router_module.router)
app.include_router(export_router_module.router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
