import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from knowledge_engine.core.logging import logger

class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log Request Start
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host
        )
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log Request Success
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=f"{process_time:.4f}s"
            )
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration=f"{process_time:.4f}s"
            )
            raise e