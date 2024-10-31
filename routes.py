from server import PromptServer
from execution import validate_prompt
from aiohttp import web
from aiohttp.web import WebSocketResponse
from aiohttp.web_request import Request
from .common import *
from . import dataReceiver

routes: web.RouteTableDef = PromptServer.instance.routes


@routes.post("/flyingshapes/push-workflow")
async def push_workflow(request: Request):
    json_data = await request.json()
    name = json_data.get("name", None)
    workflow = json_data.get("workflow", None)
    workflow_ui = json_data.get("workflow_ui", None)
    change_message = json_data.get("change_message", None)
    client_id: str = json_data.get("clientId", None) #server.client_id
    workflow_id = json_data.get("id", None)

    if workflow_id is None:
        return web.json_response({"error": "missing workflow id"}, status=400)

    if workflow is None:
        return web.json_response({"error": "missing workflow"}, status=400)

    if client_id is None:
        return web.json_response({"error": "missing client_id."}, status=400)

    server: PromptServer = PromptServer.instance

    is_fs = is_fs_id(client_id)
    if is_fs:
        # pass
        return web.json_response({"error": "workflow supposed to be sent from web ui."}, status=400)

    user_id = json_data.get("userId", None)
    if user_id is None:
        return web.json_response({"error": "missing UserId"}, status=400)

    sid_prefixes = []
    sid_prefix = json_data.get("fs_id_prefix", None)
    if sid_prefix is not None:
        sid_prefixes.append(sid_prefix)

    sid = make_fs_id(user_id, *sid_prefixes)

    sock: WebSocketResponse | None = server.sockets.get(sid, None)
    if sock is None:
        return web.json_response({"error": "no socket connection for '" + sid}, status=400)

    valid = validate_prompt(workflow)
    print("sending workflow: "+("FS ===> webui" if is_fs else "webui ===> FS"))

    if not is_fs and not valid[0]:
        print("invalid prompt: {}".format(valid[1]))
        return web.json_response({"error": valid[1], "node_errors": valid[3]}, status=400)

    response = {"message": "sending workflow to flyingshapes"}
    server.send_sync("flyingshapes_workflow", {
        "id": workflow_id,
        "name": name,
        "workflow": workflow,
        "graphApi": workflow,
        "graphUi": workflow_ui,
        "workflowChanges": change_message,
        "comfyClientId": client_id,
    }, sid)
    return web.json_response(response)


@routes.post("/flyingshapes/request-workflow-edit")
async def request_workflow_edit(request: Request):
    json_data = await request.json()
    name = json_data.get("name", None)
    timeout = json_data.get("timeout", None)
    client_id: str = json_data.get("clientId", None) #server.client_id
    user_id = json_data.get("userId", None)
    workflow_id = json_data.get("id", None)
    # workflow = json_data.get("workflow", None)
    # workflow_ui = json_data.get("workflow_ui", None)
    # if workflow is None:
    #     return web.json_response({"error": "missing workflow"}, status=400)

    if client_id is None:
        return web.json_response({"error": "missing client_id."}, status=400)
    if user_id is None:
        return web.json_response({"error": "missing UserId"}, status=400)

    is_fs = is_fs_id(client_id)
    if is_fs:
        # pass
        return web.json_response({"error": "edit-request is supposed to be sent from web ui."}, status=400)

    server: PromptServer = PromptServer.instance
    sid = make_fs_id(user_id, 'web')

    sock: WebSocketResponse | None = server.sockets.get(sid, None)
    if sock is None:
        return web.json_response({"error": "no socket connection for '" + sid}, status=400)

    print("requesting workflow from FS-Web!")

    server.send_sync("flyingshapes_workflow_edit_request", {
        "name": name,
        "id": workflow_id,
        "comfyClientId": client_id,
    }, sid)

    try:
        result = await dataReceiver.node_receive_message_async(sid, lambda x: True, timeout)
    except TimeoutError as e:
        print("TimeoutError: {0}".format(str(e)))
        msg = "timed out waiting for result after {0}seconds.".format(str(timeout))
        return web.json_response({"error": msg}, status=400)

    if "error" in result:
        error = result.get("error")
        cancelled = "cancelled" in str(error).lower()
        return web.json_response({"error": error, "cancelled": cancelled}, status=400)

    if "workflow" not in result:
        return web.json_response({"error": "missing workflow"}, status=400)

    workflow = result.get("workflow")
    print(" received workflow: " + str(workflow) + " value.")

    return web.json_response({
        "workflow": workflow
    })


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

    existing_data = FlyingShapes_extra_data.setdefault(client_id, {})

    existing_data.update(data)
    response = {"message": "fs extra data sent to comfyUi"}
    return web.json_response(response)


@routes.post("/flyingshapes/provide-input")
async def provide_input_value(request: Request):
    json_data = await request.json()
    data = json_data.get("data", None)
    error = json_data.get("error", None)
    fs_client_id = json_data.get("clientId", None)
    #fs_client_id = json_data.get("fsClientId", None)
    if data is None:
        return web.json_response({"error": "missing data"}, status=400)
    if fs_client_id is None:
        return web.json_response({"error": "missing clientId"}, status=400)

    handlers = FlyingShapes_message_handlers.setdefault(fs_client_id, set())
    was_handled = False
    for handler in handlers.copy():
        test, future = handler
        if dataReceiver.test_message(test, data):
            handlers.remove(handler)
            try:
                loop = future.get_loop()
                if error is None:
                    loop.call_soon_threadsafe(future.set_result, data)
                else:
                    loop.call_soon_threadsafe(future.set_exception, ValueError(error))
            except asyncio.CancelledError as e:
                pass
            except RuntimeError as e:   #Event loop is closed
                pass
            was_handled = True

    response = {"message": "provided input data from FS to comfyUi", "consumed": was_handled}
    return web.json_response(response)


@routes.post("/flyingshapes/fs-connection")
async def fs_connection(request: Request):
    json_data = await request.json()
    user_id = json_data.get("userId", None)
    if user_id is None:
        return web.json_response({"error": "missing UserId"}, status=400)

    sid = make_fs_id(user_id)
    sidWeb = make_fs_id(user_id, 'web')
    server: PromptServer = PromptServer.instance

    sock: WebSocketResponse | None = server.sockets.get(sid, None)
    sockWeb: WebSocketResponse | None = server.sockets.get(sidWeb, None)

    return web.json_response({
        "connected": False if sock is None else True,
        "connectedWeb": False if sockWeb is None else True,
    })


@routes.get("/flyingshapes/version")
async def fs_version(request: Request):
    return web.json_response(FsVersionInfo.data)