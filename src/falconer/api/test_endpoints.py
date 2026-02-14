"""FastAPI test endpoints for OpenClaw integration PoC."""

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
import uvicorn

from .. import __version__
from ..config import Config
from ..logging import get_logger
from ..adapters.bitcoind import BitcoinAdapter
from ..adapters.electrs import ElectrsAdapter
from ..adapters.mempool import MempoolAdapter

logger = get_logger(__name__)


def create_api_app(config: Config) -> FastAPI:
    """Factory function to create configured FastAPI app with dependency injection."""
    app = FastAPI(
        title="Falconer Test API",
        description="Test API for OpenClaw integration PoC",
        version=__version__,
    )
    app.state.config = config

    # Security and middleware setup
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API key security for OpenClaw integration
    api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

    async def get_api_key(api_key: str = Depends(api_key_header)):
        """Validate API key for OpenClaw integration."""
        # If OpenClaw integration is disabled, allow access without API key for backward compatibility
        if not config.openclaw_enabled:
            return None
        
        # If API key is configured, validate it
        if config.openclaw_api_key:
            if not api_key:
                raise HTTPException(status_code=401, detail="API key required")
            if api_key != config.openclaw_api_key:
                raise HTTPException(status_code=401, detail="Invalid API key")
        
        return api_key

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

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        """Add security headers to all responses."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with consistent error format."""
        logger.error("HTTP Exception", error=str(exc.detail), status_code=exc.status_code)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error("Unexpected error", error=str(exc), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "status_code": 500,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

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

    @app.get("/api/bitcoin/blockchain-info")
    async def get_blockchain_info(api_key: str = Depends(get_api_key)):
        """Get current blockchain information from Bitcoin node."""
        try:
            bitcoin_adapter = BitcoinAdapter(config)
            info = bitcoin_adapter.get_blockchain_info()
            bitcoin_adapter.close()
            
            return JSONResponse(
                status_code=200,
                content={
                    "blocks": info.get("blocks", 0),
                    "headers": info.get("headers", 0),
                    "chain": info.get("chain", "main"),
                    "difficulty": info.get("difficulty", 0),
                    "size_on_disk": info.get("size_on_disk", 0),
                    "pruned": info.get("pruned", False),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            logger.error("Failed to get blockchain info", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to get blockchain info")

    @app.get("/api/bitcoin/mempool-info")
    async def get_mempool_info(api_key: str = Depends(get_api_key)):
        """Get current mempool information."""
        try:
            bitcoin_adapter = BitcoinAdapter(config)
            mempool_info = bitcoin_adapter.get_mempool_info()
            bitcoin_adapter.close()
            
            return JSONResponse(
                status_code=200,
                content={
                    "loaded": mempool_info.get("loaded", False),
                    "size": mempool_info.get("size", 0),
                    "bytes": mempool_info.get("bytes", 0),
                    "usage": mempool_info.get("usage", 0),
                    "maxmempool": mempool_info.get("maxmempool", 0),
                    "mempoolminfee": mempool_info.get("mempoolminfee", 0),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            logger.error("Failed to get mempool info", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to get mempool info")

    @app.get("/api/bitcoin/fee-estimates")
    async def get_fee_estimates(api_key: str = Depends(get_api_key)):
        """Get current fee estimates for different confirmation targets."""
        try:
            bitcoin_adapter = BitcoinAdapter(config)
            estimates = bitcoin_adapter.estimate_fee_rates()
            bitcoin_adapter.close()
            
            return JSONResponse(
                status_code=200,
                content={
                    "fast": estimates.get("fast", 10),
                    "medium": estimates.get("medium", 5),
                    "slow": estimates.get("slow", 2),
                    "economical": estimates.get("economical", 1),
                    "minimum": estimates.get("minimum", 1),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            logger.error("Failed to get fee estimates", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to get fee estimates")

    @app.get("/api/bitcoin/network-stats")
    async def get_network_stats(api_key: str = Depends(get_api_key)):
        """Get Bitcoin network statistics and health indicators."""
        try:
            bitcoin_adapter = BitcoinAdapter(config)
            electrs_adapter = ElectrsAdapter(config)
            
            # Get blockchain info
            blockchain_info = bitcoin_adapter.get_blockchain_info()
            
            # Get mempool info
            mempool_info = bitcoin_adapter.get_mempool_info()
            
            # Get tip height from Electrs
            tip_height = electrs_adapter.get_tip_height()
            
            bitcoin_adapter.close()
            electrs_adapter.close()
            
            return JSONResponse(
                status_code=200,
                content={
                    "network": blockchain_info.get("chain", "main"),
                    "block_height": blockchain_info.get("blocks", 0),
                    "electrs_tip_height": tip_height,
                    "difficulty": blockchain_info.get("difficulty", 0),
                    "mempool_size": mempool_info.get("size", 0),
                    "mempool_bytes": mempool_info.get("bytes", 0),
                    "hash_rate": blockchain_info.get("difficulty", 0) * 2**32 / 600,  # Approximate
                    "is_synced": blockchain_info.get("blocks", 0) == blockchain_info.get("headers", 0),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            logger.error("Failed to get network stats", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to get network stats")

    @app.get("/api/bitcoin/market-analysis")
    async def get_market_analysis(api_key: str = Depends(get_api_key)):
        """Get AI-powered Bitcoin market analysis (simplified for OpenClaw)."""
        try:
            # This would integrate with the AI market analyzer in a full implementation
            # For PoC, return mock data
            
            return JSONResponse(
                status_code=200,
                content={
                    "fee_trend": "stable",
                    "mempool_congestion": "low",
                    "network_activity": "normal",
                    "opportunity_score": 0.75,
                    "risk_level": "medium",
                    "recommendation": "Good conditions for transactions",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            logger.error("Failed to get market analysis", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to get market analysis")

    @app.get("/api/bitcoin/address-info")
    async def get_address_info(address: str, api_key: str = Depends(get_api_key)):
        """Get information about a Bitcoin address."""
        try:
            electrs_adapter = ElectrsAdapter(config)
            
            # Get address info from Electrs
            address_info = electrs_adapter.get_address_info(address)
            
            electrs_adapter.close()
            
            return JSONResponse(
                status_code=200,
                content={
                    "address": address,
                    "balance_sats": address_info.get("balance", 0),
                    "tx_count": address_info.get("tx_count", 0),
                    "unconfirmed_balance_sats": address_info.get("unconfirmed_balance", 0),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            logger.error("Failed to get address info", error=str(e), address=address)
            raise HTTPException(status_code=400, detail=f"Invalid address or error: {str(e)}")

    @app.get("/api/bitcoin/transaction")
    async def get_transaction(tx_id: str, api_key: str = Depends(get_api_key)):
        """Get information about a Bitcoin transaction."""
        try:
            bitcoin_adapter = BitcoinAdapter(config)
            
            # Get transaction info
            tx_info = bitcoin_adapter.get_transaction(tx_id)
            
            bitcoin_adapter.close()
            
            return JSONResponse(
                status_code=200,
                content={
                    "txid": tx_id,
                    "confirmations": tx_info.get("confirmations", 0),
                    "size": tx_info.get("size", 0),
                    "weight": tx_info.get("weight", 0),
                    "fee": tx_info.get("fee", 0),
                    "fee_rate": tx_info.get("fee_rate", 0),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            logger.error("Failed to get transaction info", error=str(e), tx_id=tx_id)
            raise HTTPException(status_code=404, detail=f"Transaction not found: {str(e)}")

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
