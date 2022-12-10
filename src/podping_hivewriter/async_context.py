import asyncio
from typing import List


class AsyncContext:
    def __init__(self):
        self._tasks: List[asyncio.Task] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        try:
            for task in self._tasks:
                task.cancel()
        except RuntimeError:
            pass

        if self._tasks:
            wait_coro = asyncio.wait(
                self._tasks, timeout=3, return_when=asyncio.ALL_COMPLETED
            )
            try:
                loop = asyncio.get_running_loop()

                future = asyncio.run_coroutine_threadsafe(wait_coro, loop)
                # This is broken, pending https://bugs.python.org/issue42130
                # future.result(3)
            except RuntimeError:
                asyncio.run(wait_coro)
            except TimeoutError:
                pass
            finally:
                self._tasks = []

    def _add_task(self, task):
        self._tasks.append(task)
