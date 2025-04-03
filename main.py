import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

# Import and apply Docker-compatible logging config before any other imports
if os.environ.get('PYTHONMULTIPROCESSING') == '1':
    import logging.config
    from logging_config import LOGGING_CONFIG
    logging.config.dictConfig(LOGGING_CONFIG)

from app.api.api import router as api_router
from app.common.config import settings
from app.common.context_middleware import LogContextMiddleware
from app.common.logging import setup_logging
from app.construct import dividend_service, trade_service, storage

# Initialize logging, but only if we're not in Docker
if os.environ.get('PYTHONMULTIPROCESSING') != '1':
    setup_logging(level="INFO")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect to Bittensor
    await dividend_service.connect(warm_up=True)
    await trade_service.initialize(settings.wallet_password)

    # Start the storage service for database operations
    await storage.start()

    yield
    # Shutdown: close the connection

    await dividend_service.close()
    # Stop the storage service
    await storage.stop()


# Initialize FastAPI app
app = FastAPI(
    title="TaoPulse API",
    description="API for querying Tao dividends from the Bittensor blockchain",
    version="0.1.0",
    lifespan=lifespan,
)

# Add context middleware (must be added before other middleware)
app.add_middleware(LogContextMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router)


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}


# Run the application
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
