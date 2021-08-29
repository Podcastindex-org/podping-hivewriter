import inspect
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

from asgiref.sync import sync_to_async as _sync_to_async


thread_pool = ThreadPoolExecutor()


# Async generator wrapper from https://github.com/django/asgiref/issues/142
def sync_to_async(sync_fn, thread_sensitive=True):
    executor = thread_pool if not thread_sensitive else None
    is_gen = inspect.isgeneratorfunction(sync_fn)
    async_fn = _sync_to_async(
        sync_fn, thread_sensitive=thread_sensitive, executor=executor
    )

    if is_gen:

        @wraps(sync_fn)
        async def wrapper(*args, **kwargs):
            sync_iterable = await async_fn(*args, **kwargs)
            async_iterable = sync_to_async_iterable(sync_iterable)
            async for item in async_iterable:
                yield item

    else:

        @wraps(sync_fn)
        async def wrapper(*args, **kwargs):
            return await async_fn(*args, **kwargs)

    return wrapper


async def sync_to_async_iterable(sync_iterable):
    sync_iterator = await iter_async(sync_iterable)
    while True:
        try:
            yield await next_async(sync_iterator)
        except StopAsyncIteration:
            return


iter_async = sync_to_async(iter, thread_sensitive=False)


def _next(it):
    try:
        return next(it)
    except StopIteration:
        raise StopAsyncIteration


next_async = sync_to_async(_next, thread_sensitive=False)
