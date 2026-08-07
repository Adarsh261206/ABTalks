from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.agent_engine import AgenticInterviewEngine
from app.core.engine import InterviewEngine
from app.core.llm import LLMGateway
from app.infrastructure.llm import LLMProvider
from app.infrastructure.llm_client import OpenAICompatibleProvider
from app.infrastructure.llm_mock import MockLLMProvider
from app.routes import interview as interview_routes
from app.routes import meta as meta_routes
from app.services.interview import InterviewService
from app.services.locks import SessionLockRegistry
from app.services.ratelimit import RateLimiter
from app.state.repository import SessionRepository
from app.state.store import SqliteSessionStore

logger = logging.getLogger("viva")


def create_app(
    store: SessionRepository | None = None,
    engine: InterviewEngine | AgenticInterviewEngine | None = None,
    rate_limiter: RateLimiter | None = None,
    locks: SessionLockRegistry | None = None,
    llm_gateway: LLMGateway | None = None,
) -> FastAPI:
    """Composition root: wires repository, engine, services and providers."""
    session_store = store or SqliteSessionStore(
        db_path=settings.db_path, ttl_hours=settings.session_ttl_hours
    )
    gateway = llm_gateway or _default_llm_gateway()
    interview_engine = engine or AgenticInterviewEngine(gateway=gateway)
    limiter = rate_limiter or RateLimiter(limit=settings.rate_limit_per_minute)
    lock_registry = locks or SessionLockRegistry()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init = getattr(session_store, "init", None)
        if init is not None:
            await init()
        app.state.store = session_store
        app.state.engine = interview_engine
        app.state.rate_limiter = limiter
        app.state.locks = lock_registry
        app.state.llm_gateway = gateway
        app.state.interview_service = InterviewService(
            store=session_store, engine=interview_engine
        )
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

    # Frontend static build (served at / when dist exists) — M5 additive, non-frozen.
    dist_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if dist_dir.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=dist_dir / "assets"),
            name="assets",
        )

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa(full_path: str):
            if full_path.startswith("api/"):
                raise StarletteHTTPException(status_code=404)
            candidate = dist_dir / full_path
            if full_path and candidate.is_file() and candidate.resolve().is_relative_to(dist_dir.resolve()):
                return FileResponse(candidate)
            return FileResponse(dist_dir / "index.html")

    return app


def _default_llm_gateway() -> LLMGateway:
    """Provider ladder: configured provider → mock (demo never dies)."""
    if settings.llm_provider == "openai" and settings.openai_api_key:
        primary: LLMProvider = OpenAICompatibleProvider(
            api_key=settings.openai_api_key,
            model=settings.llm_model or "gpt-4o-mini",
            base_url=settings.llm_base_url or None,
        )
    else:
        primary = MockLLMProvider()
    return LLMGateway(primary=primary)


async def _ttl_cleanup(store: SessionRepository) -> None:
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
