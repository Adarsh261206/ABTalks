from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.engine import InterviewEngine
from app.routes import interview as interview_routes
from app.routes import meta as meta_routes
from app.state.store import SessionStore

logger = logging.getLogger("viva")


def create_app(
    store: SessionStore | None = None,
    engine: InterviewEngine | None = None,
) -> FastAPI:
    session_store = store or SessionStore(
        db_path=settings.db_path, ttl_hours=settings.session_ttl_hours
    )
    interview_engine = engine or InterviewEngine()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await session_store.init()
        app.state.store = session_store
        app.state.engine = interview_engine
        cleanup = asyncio.create_task(_ttl_cleanup(session_store))
        try:
            yield
        finally:
            cleanup.cancel()
            await session_store.close()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex[:12]
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": "Invalid request.",
                "request_id": getattr(request.state, "request_id", ""),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, exc: StarletteHTTPException):
        content = exc.detail
        if not isinstance(content, dict):
            content = {"error": str(content)}
        content.setdefault("request_id", getattr(request.state, "request_id", ""))
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error.",
                "request_id": getattr(request.state, "request_id", ""),
            },
        )

    app.include_router(interview_routes.router)
    app.include_router(meta_routes.router)
    return app


async def _ttl_cleanup(store: SessionStore) -> None:
    while True:
        try:
            await asyncio.sleep(600)
            removed = await store.cleanup_expired()
            if removed:
                logger.info("TTL cleanup removed %d session(s)", removed)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("TTL cleanup failed")


app = create_app()
