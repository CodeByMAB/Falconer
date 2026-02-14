"""FastAPI test endpoints for OpenClaw integration PoC."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .. import __version__
from ..config import Config
from ..logging import get_logger

logger = get_logger(__name__)


def create_api_app(config: Config) -> FastAPI:
    """Factory function to create configured FastAPI app with dependency injection."""
    app = FastAPI(
        title="Falconer Test API",
        description="Test API for OpenClaw integration PoC",
        version=__version__,
    )
    app.state.config = config

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all API requests for audit."""
        logger.info(
            "API request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            },
        )
        response = await call_next(request)
        return response

    @app.get("/api/health")
    async def health_check():
        """Health check endpoint for Docker and connectivity verification."""
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "service": "falconer-api",
                "version": __version__,
            },
        )

    @app.get("/api/test/fee-brief")
    async def fee_brief_test():
        """Return simplified fee intelligence data (mock) for PoC."""
        return JSONResponse(
            status_code=200,
            content={
                "current_fee_rate": 10,
                "mempool_size": 45000,
                "recommendation": "Good time for transactions",
            },
        )

    @app.post("/api/test/echo")
    async def echo_test(request: Request):
        """Echo back request payload to test request/response cycle."""
        try:
            body = await request.json()
        except Exception:
            body = {}
        return JSONResponse(status_code=200, content={"echo": body})

    return app


def run_api_server(config: Config, host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start uvicorn server for the test API."""
    app = create_api_app(config)
    logger.info(
        "Starting test API server",
        extra={"host": host, "port": port},
    )
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )
