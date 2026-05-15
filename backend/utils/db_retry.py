"""
Database retry utility — retries operations on SQLite lock errors.
"""
import time
import logging
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_MS = 300  # base delay, doubles each retry


def is_lock_error(error):
    """Check if the error is a SQLite 'database is locked' error."""
    msg = str(error).lower()
    return 'database is locked' in msg or 'operationalerror' in msg and 'locked' in msg


def retry_on_lock(func):
    """Decorator: retry the function on SQLite lock errors."""
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except OperationalError as e:
                if is_lock_error(e) and attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_MS * (2 ** attempt) / 1000.0
                    logger.warning(f'[DB] Locked on "{func.__name__}", retry {attempt + 1}/{MAX_RETRIES} in {delay:.1f}s')
                    time.sleep(delay)
                    continue
                raise
    return wrapper
