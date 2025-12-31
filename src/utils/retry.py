import time
from typing import Callable, TypeVar

T = TypeVar("T")

def retry(
    fn: Callable[[], T],
    attempts: int = 3,
    base_sleep: float = 0.4,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except exceptions as e:
            last_exc = e
            time.sleep(base_sleep * (2 ** i))
    assert last_exc is not None
    raise last_exc

