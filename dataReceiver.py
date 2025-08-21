from .common import *
from server import PromptServer
import uuid
import asyncio
import typing
from .errors import HTTPJsonResponse

# def test_message(test: common.ReceiveFilter, data: typing.Any) -> bool:
#     if isinstance(data, str) and not callable(test):
#         return False
#     if callable(test):
#         return test(data)
#     if not isinstance(test, frozenset):
#         raise TypeError(f'test must be a Function or frozen set {type(test)}')
#     if not isinstance(data, dict):
#         return False
#
#     for k, v in test:
#         if k not in data:
#             return False
#         if data.get(k) != v:
#             return False
#
#     return True

async def fs_request_value(
        request_message_type: str,
        sid: str | typing.Iterable[str] | typing.Callable[[str], bool],
        request_data: typing.Dict[str, typing.Any] = None,
        timeout: int | str | None = None
):
    server: PromptServer = PromptServer.instance
    #server.client_id
    request_data = dict() if request_data is None else request_data
    r_id: str = uuid.uuid4().hex

    request_data[fs_request_id_field] = r_id

    sids: typing.Iterable[str]
    if callable(sid):
        def s_filter(kv):
            s_id, sock = kv
            return sid(s_id) and sock is not None
        sids = [s_id for s_id, sock in filter(s_filter, server.sockets.items())]
    elif isinstance(sid, str):
        sids = [sid]
    else:
        sids = sid
    any_socks = False

    for s in sids:
        any_socks = True
        #print(f"sending {request_message_type} request to {s} - {request_data}")
        server.send_sync(request_message_type, request_data, s)

    if not any_socks:
        raise HTTPJsonResponse("no fs-web socket connection")

    #await asyncio.sleep(0)


    try:
        result = await node_receive_message_async(r_id, timeout)
    except TimeoutError as e:
        #print("TimeoutError: {0}".format(str(e)))
        msg = "timed out waiting for result after {0}seconds.".format(str(timeout))
        raise HTTPJsonResponse(msg)

    return result

# throws TimeoutError
async def node_receive_message_async(r_id: str,
                                     timeout: int | str | None = None):

    if r_id in FlyingShapes_message_handlers:
        raise Exception(f"No handler registered for {r_id}")

    loop = asyncio.get_running_loop()
    future = loop.create_future()

    FlyingShapes_message_handlers[r_id] = future

    if isinstance(timeout, str):
        timeout = float(timeout) if timeout.isnumeric() else None

    result = await asyncio.wait_for(future, timeout)
    return result