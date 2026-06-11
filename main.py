import logging
from contextlib import asynccontextmanager

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
_memory_service_url = getattr(settings, "memory_id", None)
recall_svc = RecallService(store=store, memory_service_url=_memory_service_url)
stats_svc = StatsService(store=store)
export_svc = ExportService(store=store)

# Inject services into routers BEFORE include_router
recall_router_module.recall_service = recall_svc
stats_router_module.stats_service = stats_svc
export_router_module.export_service = export_svc


@asynccontextmanager
async def lifespan(app: FastAPI):
    stats = await store.load_stats()
    logger.info(
        "AKC starting — KB_DIR: %s, patterns: %d",
        settings.akc_kb_dir,
        stats["total_patterns"],
    )
    yield
    logger.info("AKC shutting down")


app = FastAPI(
    title="AKC — Agent Knowledge Collective",
    version="0.1.0",
    lifespan=lifespan,
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
