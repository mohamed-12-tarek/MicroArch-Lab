"""HTTP routes: the three endpoints agreed in ``docs/api-contract.md``.

Owner: M1.  Routes only translate HTTP <-> service calls; every rule lives in
:mod:`app.api.service` so it can be tested without a web server.

======================  =========================================  ==========
Endpoint                Body                                       Success
======================  =========================================  ==========
GET  /api/health        -                                          200
POST /api/simulate      ``{"code": "..."}``                        200
POST /api/simulate/upload  multipart field ``file`` (``.asm``)      200
======================  =========================================  ==========

Failures
--------
* invalid assembly -> **200** with ``success: false`` and ``errors[]``
* missing ``code``  -> **422** (FastAPI validation)
* not ``.asm``      -> **400**
* bigger than 100KB -> **413**
"""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from ..core.errors import MAX_FILE_SIZE_BYTES, FileTooLargeError
from ..schemas.simulation import HealthResponse, SimulateRequest, SimulationResponse
from . import service

router = APIRouter(prefix="/api", tags=["simulation"])

_CHUNK_SIZE = 64 * 1024


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns ``status: ok`` plus the API version and which engine is wired in.",
)
def health() -> HealthResponse:
    return service.health()


@router.post(
    "/simulate",
    response_model=SimulationResponse,
    summary="Simulate assembly source code",
    responses={
        422: {"description": "Missing or malformed body"},
    },
)
def simulate(request: SimulateRequest) -> SimulationResponse:
    return service.simulate_code(request.code)


@router.post(
    "/simulate/upload",
    response_model=SimulationResponse,
    summary="Simulate an uploaded .asm file",
    responses={
        400: {"description": "Not a .asm file"},
        413: {"description": "File bigger than 100KB"},
    },
)
async def simulate_upload(
    file: UploadFile = File(..., description="Assembly source file (.asm, max 100KB)"),
) -> SimulationResponse:
    content = await _read_limited(file)
    return service.simulate_upload(file.filename, content)


async def _read_limited(file: UploadFile) -> bytes:
    """Read the upload in chunks and stop as soon as it passes the limit."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_FILE_SIZE_BYTES:
            raise FileTooLargeError(
                f"File is too large: more than {MAX_FILE_SIZE_BYTES} bytes "
                f"(maximum {MAX_FILE_SIZE_BYTES} bytes)"
            )
        chunks.append(chunk)
    return b"".join(chunks)
