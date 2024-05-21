import json
from .dataReceiver import *
from .common import *

from server import PromptServer
from aiohttp.web import WebSocketResponse
import base64
from PIL import Image
from io import BytesIO
import numpy as np
import torch


class FsInputNode:
    FUNCTION = "receive_value"
    OUTPUT_NODE = False
    FS_CLASS_LABEL = None

    def class_name(self):
        return type(self).__name__

    def IS_CHANGED(self, **kwargs):
        return float("NaN")  # time.time()

    def process_value(self, value):
        return (value,)

    def fs_request_data(self, **kwargs):
        return {
            "type": to_snake_case(self.class_name()),
            "name": kwargs.get("name"),
        }

    def fs_response_test(self, **kwargs) -> ReceiveFilterOrDict:
        return self.fs_request_data(**kwargs)

    def fs_request_message_type(self, **kwargs):
        return "flyingshapes_request"

    def receive_value(self, **kwargs):
        stored_value = kwargs.get("stored_value", None)
        server: PromptServer = PromptServer.instance
        client_id: str = server.client_id
        is_fs = client_id.startswith(fs_sid_prefix)

        fs_data = FlyingShapes_extra_data.get(client_id, None)
        fs_sid = None

        if is_fs:
            if stored_value is None:
                raise Exception(self.class_name()+": Missing stored value")
            return self.process_value(stored_value)

        err = "Prompt not sent from Flyingshapes and: "
        if fs_data is None:
            # raise Exception(err + "fs_data is None.")
            print(err + "fs_data is None.")
            return self.process_value(stored_value)

        user_id: str | None = fs_data.get("userId", None)
        timeout = fs_data.get("timeout", None)
        if user_id is None or len(user_id) == 0:
            raise Exception(err + "None or empty userId.")
        fs_sid = fs_sid_prefix + user_id

        sock: WebSocketResponse | None = server.sockets.get(client_id, None)
        if sock is None:  # or queue is None:
            raise Exception("no socket connection for '" + fs_sid)

        request_data = self.fs_request_data(**kwargs)
        request_message_type = self.fs_request_message_type(**kwargs)
        response_test = self.fs_response_test(**kwargs)

        server.send_sync(request_message_type, request_data, fs_sid)

        print("sent " + request_message_type + " message, waiting for result")
        try:
            result = node_receive_message(fs_sid, response_test, timeout)
        except TimeoutError as e:
            print("TimeoutError: {0}".format(str(e)))
            msg = "{0} timed out waiting for result after {1}seconds.".format(self.class_name(), str(timeout))
            raise Exception(msg)

        if "value" not in result:
            raise Exception("Missing value in result")
        value = result.get("value")

        print(self.class_name()+" received " + str(type(value)) + " value.")

        return self.process_value(value)


class InputSlider(FsInputNode):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "name": ("STRING", {"default": "influence"}),
                "min_val": ("FLOAT", {"default": 0.0, }),  # "min": 0.01, "max": 16.0, "step": 0.01
                "max_val": ("FLOAT", {"default": 1.0, }),
                "order": ("INT", {"default": 1, "min": 0, }),
                "stored_value": ("FLOAT", {"default": 0.0, }),
            },
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("Slider Value (FLOAT)",)
    CATEGORY = "flyingshapes/slider"
    FS_CLASS_LABEL = "Slider"


class InputText(FsInputNode):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "name": ("STRING", {"default": "influence"}),
                "order": ("INT", {"default": 1, "min": 0, }),
                "stored_value": ("STRING", {"default": "", }),
                "placeholder": ("STRING", {"default": "", }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("Text (STRING)",)
    CATEGORY = "flyingshapes/text"
    FS_CLASS_LABEL = "Text"


class InputScreenShot(FsInputNode):
    screenshot_types = ["default", "depth", "normal", "sketch"]

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "type": (s.screenshot_types,),
                "width": ("INT", {"default": 912, "min": 12, }),
                "height": ("INT", {"default": 512, "min": 12, }),
                "stored_value": ("STRING", {"default": 0.0, }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("Screenshot (IMAGE)",)
    CATEGORY = "flyingshapes/screenshot"
    FS_CLASS_LABEL = "Image"

    def process_value(self, value):
        imgdata = base64.b64decode(value)
        img = Image.open(BytesIO(imgdata))

        # if "A" in img.getbands():
        #     mask = np.array(img.getchannel("A")).astype(np.float32) / 255.0
        #     mask = 1.0 - torch.from_numpy(mask)
        # else:
        #     mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")

        img = img.convert("RGB")
        img = np.array(img).astype(np.float32) / 255.0
        img = torch.from_numpy(img)[None,]

        return (img,)
        # return (img, mask)

    def fs_request_data(self, type=None, height=512, width=910, **kwargs):
        return {
            "type": type if type is not None else self.screenshot_types[0],
            "height": height,
            "width": width,
        }

    def fs_response_test(self, type=None, **kwargs) -> ReceiveFilterOrDict:
        return {
            "type": type if type is not None else self.screenshot_types[0],
        }


    def fs_request_message_type(self, **kwargs):
        return "flyingshapes_request_screenshot"
