from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.common.context import log_context_var, generate_request_id, default_context


class LogContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that sets up context variables for each request.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        # Create a new context for this request
        context = default_context.copy()

        # Generate a unique request ID
        request_id = generate_request_id()
        context["request_id"] = request_id

        # Set the context
        token = log_context_var.set(context)

        try:
            # Process the request without logging
            response = await call_next(request)
            return response
        except Exception:
            # Still log exceptions
            raise
        finally:
            # Reset the context to avoid leaking between requests
            log_context_var.reset(token)
