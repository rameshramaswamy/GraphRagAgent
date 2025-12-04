from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from services.api.routers import chat, ingest
from services.api.middleware import RequestLogMiddleware
from services.api.security import get_api_key
from knowledge_engine.core.logging import configure_logging, logger
from knowledge_engine.core.database import GraphDatabaseManager
from services.api.routers import chat, ingest, ws 
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from services.api.limiter import limiter
import signal
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    configure_logging()
    logger.info("api_startup")
    GraphDatabaseManager.get_instance()
    
    # Handle SIGTERM (Docker Stop) for graceful cleanup
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.warning("shutdown_signal_received")
        stop_event.set()
        
    # Register signal handler if supported (Unix)
    try:
        loop.add_signal_handler(signal.SIGTERM, signal_handler)
    except NotImplementedError:
        pass # Windows doesn't support add_signal_handler fully in some loops

    yield
    
    # --- SHUTDOWN ---
    logger.info("api_shutdown_commencing")
    
    # Close DB Driver
    try:
        GraphDatabaseManager.get_instance().close()
        logger.info("neo4j_connection_closed")
    except Exception:
        pass

# 2. App Definition
app = FastAPI(
    title="Enterprise GraphRAG Platform",
    version="1.0.0",
    description="Secure, Observable, and Scalable GenAI Agent API",
    lifespan=lifespan,
    # Enforce Auth Globally (except for /health and /docs which we can exclude via overrides if needed)
    # dependencies=[Depends(get_api_key)] 
)

# 3. Observability (Prometheus Metrics)
Instrumentator().instrument(app).expose(app)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# 4. Middleware
app.add_middleware(RequestLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Tighten this in PROD
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Global Error Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Reference ID: <LogID>"}
    )

# 6. Routers
app.include_router(chat.router, dependencies=[Depends(get_api_key)])
app.include_router(ingest.router, dependencies=[Depends(get_api_key)])
app.include_router(ws.router)
# 7. Deep Health Check
@app.get("/health", tags=["System"])
def health_check():
    """Verifies dependencies are reachable."""
    status = {"api": "online", "db": "unknown", "redis": "unknown"}
    
    # Check Neo4j
    try:
        db = GraphDatabaseManager.get_instance()
        if db.health_check():
            status["db"] = "connected"
        else:
            status["db"] = "unreachable"
    except Exception as e:
        status["db"] = f"error: {str(e)}"
    
  
    return status