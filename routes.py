from server import PromptServer
from execution import validate_prompt
from aiohttp import web
from aiohttp.web import WebSocketResponse
from aiohttp.web_request import Request
from . import common, dataReceiver

routes: web.RouteTableDef = PromptServer.instance.routes


@routes.post("/flyingshapes/push-workflow")
async def push_workflow(request: Request):
    json_data = await request.json()
    name = json_data.get("name", None)
    workflow = json_data.get("workflow", None)
    if workflow is None:
        return web.json_response({"error": "missing workflow"}, status=400)

    server: PromptServer = PromptServer.instance
    sid: str = json_data.get("clientId", server.client_id)
    is_fs = sid is None or sid.startswith(common.fs_sid_prefix)

    if is_fs:
        # pass
        return web.json_response({"error": "workflow supposed to be sent from web ui."}, status=400)
    else:
        user_id = json_data.get("userId", None)
        if user_id is None:
            return web.json_response({"error": "missing UserId"}, status=400)

        sid = common.fs_sid_prefix + user_id

        sock: WebSocketResponse | None = server.sockets.get(sid, None)
        if sock is None:
            return web.json_response({"error": "no socket connection for '" + sid}, status=400)

    valid = validate_prompt(workflow)
    print("sending workflow: "+("FS ===> webui" if is_fs else "webui ===> FS"))

    if not is_fs and not valid[0]:
        print("invalid prompt: {}".format(valid[1]))
        return web.json_response({"error": valid[1], "node_errors": valid[3]}, status=400)

    response = {"message": "sending workflow to flyingshapes"}
    server.send_sync("flyingshapes_workflow", {"workflow": workflow, "name": name}, sid)
    return web.json_response(response)


@routes.post("/flyingshapes/extra-data")
async def set_extra_data(request: Request):
    json_data = await request.json()
    data = json_data.get("extraData", None)
    client_id = json_data.get("clientId", None)
    #user_id = json_data.get("userId", None)
    if data is None:
        return web.json_response({"error": "missing extraData"}, status=400)
    if client_id is None:
        return web.json_response({"error": "missing clientId"}, status=400)
    if not isinstance(data, dict):
        return web.json_response({"error": "data must be a dictionary"}, status=400)

    existing_data = common.FlyingShapes_extra_data.setdefault(client_id, {})

    existing_data.update(data)
    response = {"message": "fs extra data sent to comfyUi"}
    return web.json_response(response)


@routes.post("/flyingshapes/provide-input")
async def provide_input_value(request: Request):
    json_data = await request.json()
    data = json_data.get("data", None)
    fs_client_id = json_data.get("clientId", None)
    #fs_client_id = json_data.get("fsClientId", None)
    if data is None:
        return web.json_response({"error": "missing data"}, status=400)
    if fs_client_id is None:
        return web.json_response({"error": "missing clientId"}, status=400)

    handlers = common.FlyingShapes_message_handlers.setdefault(fs_client_id, set())
    was_handled = False
    for handler in handlers.copy():
        test, future = handler
        if dataReceiver.test_message(test, data):
            handlers.remove(handler)
            future.get_loop().call_soon_threadsafe(future.set_result, data)
            was_handled = True

    response = {"message": "provided node input data from FS to comfyUi", "consumed": was_handled}
    return web.json_response(response)


@routes.post("/flyingshapes/fs-connection")
async def push_workflow(request: Request):
    json_data = await request.json()
    user_id = json_data.get("userId", None)
    if user_id is None:
        return web.json_response({"error": "missing UserId"}, status=400)

    sid = common.fs_sid_prefix + user_id
    server: PromptServer = PromptServer.instance

    sock: WebSocketResponse | None = server.sockets.get(sid, None)

    return web.json_response({"connected": False if sock is None else True})
