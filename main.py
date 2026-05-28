import logging
import sys

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import analyze, benchmark, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("codesense")

app = FastAPI(
    title="CodeSense",
    description="AI Code Evaluation Service - analyze Python code quality and benchmark solutions.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# allow all origins in dev, restrict in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return a cleaner 422 instead of raw pydantic error dump."""
    messages = []
    for error in exc.errors():
        loc = " -> ".join(str(part) for part in error["loc"])
        messages.append(f"{loc}: {error['msg']}")
    detail = "; ".join(messages)
    logger.warning("Validation error: %s", detail)
    return JSONResponse(status_code=422, content={"detail": detail})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all so we never leak internal details to clients."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected internal error occurred."})


# register all route handlers
app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(benchmark.router)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("CodeSense v1.0.0 starting up")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("CodeSense shutting down")
