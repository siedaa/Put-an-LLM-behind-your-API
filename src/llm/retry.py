import random
import time
from collections.abc import Callable

from openai import APITimeoutError, APIStatusError, RateLimitError


def _get_retry_after(exc: RateLimitError) -> float:
    """Extract Retry-After header from a 429 response, default to 5s."""
    try:
        retry_after = exc.response.headers.get("retry-after")
        if retry_after:
            return float(retry_after)
    except (ValueError, TypeError):
        pass
    return 5.0


def _is_retryable(exc: Exception) -> bool:
    """Check if an exception is retryable (timeout, 429, 5xx)."""
    if isinstance(exc, APITimeoutError):
        return True
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code >= 500
    return False


def _is_terminal(exc: Exception) -> bool:
    """Check if an exception is terminal (400, 401, 403) — never retry."""
    if isinstance(exc, APIStatusError):
        return exc.status_code in (400, 401, 403)
    return False


def call_with_retry(call_fn: Callable) -> any:
    """Call call_fn() with retry logic for transient errors.

    - Retries on: timeout, 429, 5xx
    - Never retries on: 400, 401, 403
    - Exponential backoff with jitter: 2^attempt + random(0,1)
    - Respects Retry-After header on 429
    - Up to 3 total attempts
    - Raises the final exception if all retries exhausted
    """
    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            return call_fn()
        except Exception as exc:
            if _is_terminal(exc):
                raise
            if attempt == max_attempts - 1:
                raise
            if not _is_retryable(exc):
                raise

            if isinstance(exc, RateLimitError):
                wait = _get_retry_after(exc)
            else:
                wait = (2 ** attempt) + random.uniform(0, 1)

            time.sleep(wait)
