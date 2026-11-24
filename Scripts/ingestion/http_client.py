"""Shared HTTP client: GET with retries and exponential backoff."""

import logging
import os
import time

import requests

from Scripts.ingestion import config

log = logging.getLogger(__name__)

# Worth retrying: rate limit and temporary server errors.
RETRY_STATUSES = {429, 500, 502, 503, 504}


def get_with_retry(url, params=None, sleep=time.sleep):
    """Return the response, retrying temporary failures. Raise after the last attempt.

    Permanent errors (for example 403 for a wrong API key) are raised at once.
    """
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=config.TIMEOUT_SECONDS)
            if response.status_code in RETRY_STATUSES:
                raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
            response.raise_for_status()
            return response
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as error:
            status = getattr(getattr(error, "response", None), "status_code", None)
            retryable = status is None or status in RETRY_STATUSES
            log.warning("Attempt %d/%d failed for %s: %s", attempt, config.MAX_RETRIES, url, error)
            if not retryable or attempt == config.MAX_RETRIES:
                raise
            sleep(config.BACKOFF_SECONDS * 2 ** (attempt - 1))
    raise RuntimeError("unreachable")


def require_env(name):
    """Read a required secret from the environment, with a clear error if missing."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing {name}. Set it in Docker/.env or as a GitHub secret.")
    return value
