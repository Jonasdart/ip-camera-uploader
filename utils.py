import time
from functools import wraps
from typing import Callable


def retry(sleep_time: int = 5, max_attempts: int = 3):
    """Execute retry of a function at 3 attempts.

    Args:
        sleep_time (int): The interval of attempts
    """

    def decorator(f: Callable):
        @wraps(f)
        def wrapper(*args, **kwargs):
            errors = []
            attempts = 0
            while attempts < max_attempts:
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    errors.append(e)
                    attempts += 1
                    print(
                        f"Failed to execute {f.__name__} with:"
                        f"args {args} and kwargs {kwargs}."
                        f"Retrying in {sleep_time} seconds (Attempt {attempts}/{max_attempts})."
                    )
                    time.sleep(sleep_time)

            raise Exception(errors)

        return wrapper

    return decorator
