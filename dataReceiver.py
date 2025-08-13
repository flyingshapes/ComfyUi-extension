import typing
import asyncio
from . import common


def test_message(test: common.ReceiveFilter, data: typing.Any) -> bool:
    if isinstance(data, str) and not callable(test):
        return False
    if callable(test):
        return test(data)
    if not isinstance(test, frozenset):
        raise TypeError(f'test must be a Function or frozen set {type(test)}')
    if not isinstance(data, dict):
        return False

    for k, v in test:
        if k not in data:
            return False
        if data.get(k) != v:
            return False

    return True


# throws TimeoutError
async def node_receive_message_async(sid, test: common.ReceiveFilterOrDict,
                                     timeout: int | str | None = None):
    loop = asyncio.get_running_loop()
    future = loop.create_future()

    handlers = common.FlyingShapes_message_handlers.setdefault(sid, set())
    if isinstance(test, dict):
        test = frozenset(test.items())
    handler = (test, future)
    handlers.add(handler)

    if isinstance(timeout, str):
        timeout = float(timeout) if timeout.isnumeric() else None

    result = await asyncio.wait_for(future, timeout)
    return result