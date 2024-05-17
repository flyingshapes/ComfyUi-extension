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


def node_receive_message(sid, test: common.ReceiveFilterOrDict,
                         timeout: int | str | None = None) -> dict:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    future: asyncio.Future = loop.create_future()
    handlers = common.FlyingShapes_message_handlers.setdefault(sid, set())
    if isinstance(test, dict):
        test = frozenset(test.items())
    handler = (test, future)
    handlers.add(handler)

    if isinstance(timeout, str) and timeout.isnumeric():
        timeout = float(timeout)

    if isinstance(timeout, int | float):
        future: typing.Awaitable = asyncio.wait_for(future, timeout)
    result = loop.run_until_complete(future)
    loop.close()
    asyncio.set_event_loop(None)

    return result
