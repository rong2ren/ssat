"""FastAPI application for SSAT question generation."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException
from loguru import logger

# Import configuration and routers
from app.routers import health_router, generation_router, admin_router, user_router
from app.auth import router as auth_router
from app.specifications import OFFICIAL_ELEMENTARY_SPECS

# Global config variable
config = None

# Create FastAPI app
app = FastAPI(
    title="SSAT Question Generator API",
    description="Generate high-quality SSAT elementary level questions and complete practice tests",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware with default development settings
# Will be updated during startup if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Default to allow all in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    global config
    from app.config.app_config import get_app_config
    config = get_app_config()
    
    logger.info("SSAT Question Generator API initialized successfully")


# Include all routers
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(generation_router)
app.include_router(user_router)
app.include_router(admin_router)


# Add specifications endpoint directly to main app
@app.get("/specifications/official-format")
async def get_official_format_specification():
    """Get the official SSAT elementary format specification."""
    return OFFICIAL_ELEMENTARY_SPECS


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500}
    )

