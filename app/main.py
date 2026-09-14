from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import setup_logging, log_event
from app.db.session import init_db
from app.api import health, sessions, chat, artifacts


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize logging and database tables
    setup_logging()
    log_event("SYSTEM", "Starting The Lenny Growth Assistant service...")
    await init_db()
    log_event(
        "SYSTEM",
        "Active Configuration",
        provider=settings.LLM_PROVIDER,
        model=settings.active_model,
        embedding_model=settings.EMBEDDING_MODEL
    )
    yield
    log_event("SYSTEM", "Shutting down service...")


app = FastAPI(
    title="The Lenny Growth Assistant",
    description="Full-stack AI assistant grounded in 300+ Lenny's Podcast transcripts with Ship 30 for 30 essay generation and sandboxed artifact rendering.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Structured Error Handlers (No bare 500s or messy unhandled stack traces)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    clean_errors = [{"field": " -> ".join(str(loc) for loc in err["loc"]), "message": err["msg"]} for err in errors]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Invalid request payload.",
            "details": clean_errors
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log_event("API", f"Unhandled server error: {exc}", level=50)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected server error occurred. Please check server logs for details.",
            "status_code": 500
        }
    )


# Include Routers
app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(artifacts.router)


@app.get("/api/info", tags=["Info"])
async def get_app_info():
    """Returns active runtime configuration for UI display."""
    return {
        "app_name": "The Lenny Growth Assistant",
        "active_provider": settings.LLM_PROVIDER,
        "active_model": settings.active_model,
        "embedding_model": settings.EMBEDDING_MODEL,
        "providers_supported": ["ollama", "gemini", "claude", "openai"],
        "available_models": {
            "gemini": ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.7-flash", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
            "ollama": [settings.OLLAMA_MODEL],
            "claude": [settings.ANTHROPIC_MODEL, "claude-3-5-haiku-20241022"],
            "openai": [settings.OPENAI_MODEL, "gpt-4o-mini"]
        }
    }
