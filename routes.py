from execution import validate_prompt
from aiohttp import web
from aiohttp.web import WebSocketResponse
from aiohttp.web_request import Request
from .dataReceiver import *
from .validation import Validation
from .config import config

routes: web.RouteTableDef = PromptServer.instance.routes

@routes.post("/flyingshapes/push-workflow")
async def push_workflow(request: Request):
    v = await Validation.get(request)
    name = v.validate("name", str, None)
    workflow = v.validate("workflow", dict)
    workflow_ui = v.validate("workflow_ui", dict, None)
    change_message = v.validate("change_message", str, None)
    client_id = v.validate("clientId", str) #server.client_id
    workflow_id = v.validate("id", str)


    server: PromptServer = PromptServer.instance

    is_fs = is_fs_id(client_id)
    if is_fs:
        # pass
        return web.json_response({"error": "workflow supposed to be sent from web ui."}, status=400)

    user_id = v.validate("userId", str)

    sid_prefixes = []
    sid_prefix: str | None = v.data.get("fs_id_prefix", None)
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
    v = await Validation.get(request)
    name = v.validate("name", str, None)
    timeout = v.validate("timeout", int, None)
    client_id = v.validate("clientId", str) #server.client_id
    user_id = v.validate("userId", str)
    workflow_id = v.validate("id", dict, None)
    # workflow = json_data.get("workflow", None)
    # workflow_ui = json_data.get("workflow_ui", None)
    # if workflow is None:
    #     return web.json_response({"error": "missing workflow"}, status=400)

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
    request_data = {
        "name": name,
        "id": workflow_id,
        "comfyClientId": client_id,
    }

    result = await fs_request_value("flyingshapes_workflow_edit_request", sid, request_data, timeout)
    # try:
    # except TimeoutError as e:
    #     print("TimeoutError: {0}".format(str(e)))
    #     msg = "timed out waiting for result after {0}seconds.".format(str(timeout))
    #     return web.json_response({"error": msg}, status=400)
    # except ResponseError as e:
    #     return e.response()

    if "workflow" not in result:
        return web.json_response({"error": "missing workflow"}, status=400)

    workflow = result.get("workflow")
    print(" received workflow: " + str(workflow) + " value.")

    return web.json_response({
        "workflow": workflow
    })


@routes.post("/flyingshapes/request-fs-web-user-id")
async def request_fs_web_user_id(request: Request):
    v = await Validation.get(request)
    timeout = v.validate("timeout", int, None)
    client_id = v.validate("clientId", str)

    is_fs = is_fs_id(client_id)
    if is_fs:
        return web.json_response({"error": "edit-request is supposed to be sent from web ui."}, status=400)

    print("requesting fs uuid from FS-Web!")

    request_data = {
        "comfyClientId": client_id,
    }
    result = await fs_request_value("flyingshapes_workflow_fsUserId_request", is_fs_web_id, request_data, timeout)
    # try:
    #     #result = await node_receive_message_async(timeout=timeout)
    # except TimeoutError as e:
    #     print("TimeoutError: {0}".format(str(e)))
    #     msg = "timed out waiting for result after {0}seconds.".format(str(timeout))
    #     return web.json_response({"error": msg}, status=400)
    # except NoSocketsError:
    #     return web.json_response({"error": "no fs-web socket connection'"}, status=400)
    # except ResponseError as e:
    #     return e.response()

    if "error" in result:
        error = result.get("error")
        cancelled = "cancelled" in str(error).lower()
        return web.json_response({"error": error, "cancelled": cancelled}, status=400)

    if "fsUser" not in result:
        return web.json_response({"error": "missing fsUser"}, status=400)

    return web.json_response(result)


@routes.post("/flyingshapes/extra-data")
async def set_extra_data(request: Request):
    v = await Validation.get(request)
    data = v.validate("extraData", dict, None)
    client_id = v.validate("clientId", str)
    #user_id = v.validate("userId", str)
    existing_data = FlyingShapes_extra_data.setdefault(client_id, {})

    existing_data.update(data)
    response = {"message": "fs extra data sent to comfyUi"}
    return web.json_response(response)


@routes.post("/flyingshapes/provide-input")
async def provide_input_value(request: Request):
    v = await Validation.get(request)
    data = v.validate("data", dict)
    error: str | None = v.data.get("error", None)
    request_id = v.validate(fs_request_id_field, (str, "request id"))
    #fs_client_id = v.validate("clientId", str)

    future = FlyingShapes_message_handlers.get(request_id, None)
    has_handler = future is not None
    response = {"message": "provided input data from FS to comfyUi", "consumed": has_handler}

    if has_handler:
        try:
            loop = future.get_loop()
            if error is None:
                loop.call_soon_threadsafe(future.set_result, data)
            else:
                cancelled = "cancelled" in str(error).lower()
                loop.call_soon_threadsafe(
                    future.set_exception,
                    HTTPJsonResponse(
                        error,
                        response=v.data,
                        cancelled=cancelled
                    ))
            # noinspection PyAsyncCall
            FlyingShapes_message_handlers.pop(request_id, None)
        except asyncio.CancelledError as e:
            pass
        except RuntimeError as e:   #Event loop is closed
            pass

    return web.json_response(response)


@routes.post("/flyingshapes/fs-connection")
async def fs_connection(request: Request):
    v = await Validation.get(request)
    user_id = v.validate("userId", str)

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
    return web.json_response(text=config.model_dump_json(exclude_none=True))
