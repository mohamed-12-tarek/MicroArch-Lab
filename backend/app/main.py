"""FastAPI application entry point.

Owner: M1.  Run it with::

    cd backend
    uvicorn app.main:app --reload --port 8000

Then open http://127.0.0.1:8000/docs for the interactive API.

Responsibilities
----------------
* create the app and mount the ``/api`` router
* allow the React dev server (Vite on 5173, CRA on 3000) through CORS
* turn every :class:`app.core.errors.MicroArchError` into the documented JSON
"""

from __future__ import annotations

import os
from typing import List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import router as api_router
from .core.errors import MicroArchError

VERSION = "1.0.0"
TITLE = "MicroArch Lab API"
DESCRIPTION = (
    "Cycle-accurate 5-stage pipeline simulator (IF → ID → EX → MEM → WB).\n\n"
    "POST assembly code, get back one snapshot per cycle: which instruction is "
    "in which stage, every forwarded value, the 32 registers and the data memory."
)

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def _cors_origins() -> List[str]:
    """``MICROARCH_CORS_ORIGINS`` (comma separated) overrides the defaults."""
    raw = os.getenv("MICROARCH_CORS_ORIGINS", "")
    if not raw.strip():
        return list(DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app() -> FastAPI:
    app = FastAPI(
        title=TITLE,
        version=VERSION,
        description=DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        # Any port on localhost is fine during development.
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {
            "name": TITLE,
            "version": VERSION,
            "docs": "/docs",
            "health": "/api/health",
        }

    @app.exception_handler(MicroArchError)
    async def microarch_error_handler(request: Request, exc: MicroArchError) -> JSONResponse:
        return JSONResponse(
            status_code=getattr(exc, "status_code", 500),
            content={"detail": str(exc), "type": exc.error_type},
        )

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
