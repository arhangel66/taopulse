import contextvars
import uuid
from typing import Dict, Any

# Set up the context variable with default values
default_context = {"request_id": "", "hotkey": "", "netuid": ""}
log_context_var = contextvars.ContextVar(
    "log_context",
    default=default_context.copy(),
)


def update_log_context(**kwargs) -> None:
    """
    Update the current log context with the provided key-value pairs.

    Args:
        **kwargs: Key-value pairs to add to the context
    """
    context = log_context_var.get()
    context.update(kwargs)
    log_context_var.set(context)


def get_log_context() -> Dict[str, Any]:
    """
    Get the current log context.

    Returns:
        The current log context dictionary
    """
    return log_context_var.get()


def generate_request_id() -> str:
    """
    Generate a unique request ID.

    Returns:
        A string containing a unique request ID
    """
    return str(uuid.uuid4())[-12:]


def reset_context() -> None:
    """
    Reset the context to default values.
    """
    log_context_var.set(default_context.copy())
