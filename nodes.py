import json

from .dataReceiver import *
from .common import *
from .imgUtil import *

from server import PromptServer
from aiohttp.web import WebSocketResponse
import comfy.model_management
import comfy.utils
import torch
import time

NaN = float("NaN")

class FsInputNode:
    FUNCTION = "receive_value"
    OUTPUT_NODE = False
    FS_CLASS_LABEL = None
    CATEGORY = "flyingshapes"

    def class_name(self):
        return type(self).__name__

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        if cls.should_execute_non_interactive(**kwargs):
            return kwargs.get("stored_value", NaN)
        return NaN  # time.time()

    def process_value(self, value: str | None, **kwargs):
        return (value,)

    def fs_request_data(self, **kwargs):
        return {
            "type": to_snake_case(self.class_name()),
            "name": kwargs.get("name"),
        }

    def fs_response_test(self, response_data, **kwargs):
        # can be implemented in nodes and throw an exception if the response data is incorrect
        pass

    def fs_request_message_type(self, **kwargs):
        return "flyingshapes_request"

    def value_required(self, **kwargs) -> bool:
        return True

    @staticmethod
    def should_execute_non_interactive(**kwargs) -> bool:
        server: PromptServer = PromptServer.instance
        client_id: str = server.client_id
        is_fs = is_fs_id(client_id)

        fs_data = FlyingShapes_extra_data.get(client_id, None)

        if is_fs:
            return True

        if fs_data is None:
            # raise Exception(err + "fs_data is None.")
            print("Prompt not sent from Flyingshapes and fs_data is None.")
            return True

        use_fs_input: bool | None = fs_data.get("inputFromFs", None)
        if not use_fs_input:
            return True

        return False


    async def receive_value(self, **kwargs):
        stored_value: str | None = kwargs.get("stored_value", None)
        server: PromptServer = PromptServer.instance
        client_id: str = server.client_id

        fs_data = FlyingShapes_extra_data.get(client_id, None)
        value_required = self.value_required(**kwargs)

        if self.should_execute_non_interactive(**kwargs):
            if stored_value is None and value_required:
                raise Exception(self.class_name() + ": Missing stored value")

            return self.process_value(stored_value, **kwargs)

        user_id: str | None = fs_data.get("userId", None)
        timeout = fs_data.get("timeout", None)
        if user_id is None or len(user_id) == 0:
            v = "None" if user_id is None else "an empty string"
            raise Exception(f"userId is {v}.")
        fs_sid = make_fs_id(user_id)

        sock: WebSocketResponse | None = server.sockets.get(client_id, None)
        if sock is None:  # or queue is None:
            raise Exception("no socket connection for '" + fs_sid)

        request_data = self.fs_request_data(**kwargs)
        request_message_type = self.fs_request_message_type(**kwargs)

        print(f"sending request message of type '{request_message_type}' to flyingshapes - waiting for result")
        print(json.dumps(request_data))
        try:
            # result = await node_receive_message_async(fs_sid, response_test, timeout)
            result = await fs_request_value(request_message_type, fs_sid, request_data, timeout)
        except TimeoutError as e:
            print("TimeoutError: {0}".format(str(e)))
            msg = "{0} timed out waiting for result after {1}seconds.".format(self.class_name(), str(timeout))
            raise Exception(msg)

        self.fs_response_test(result, **kwargs)

        if "value" not in result:
            if value_required:
                raise Exception("Missing value in result")
            print(self.class_name() + " received no value (None).")
            value = None
        else:
            value = result.get("value")
            print(self.class_name() + " received " + str(type(value)) + " value.")

        return self.process_value(value, **kwargs)


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
    FS_CLASS_LABEL = "Text"


class InputStyle(FsInputNode):
    def __init__(self):
        self.device = comfy.model_management.intermediate_device()

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "order": ("INT", {"default": 1, "min": 0, }),
            },
            "optional": {
                "stored_value": ("STRING", { "forceInput": True, "default": empty_base64_image, }),
                "style_name": ("STRING", { "forceInput": True, "placeholder": "using style selected in client" }),
                "fallback_style": ("IMAGE",),
                "weight": ("FLOAT", { "forceInput": True, "min": -1, "max": 3, "step": 0.05 }),
            }
        }

    RETURN_TYPES = ("IMAGE", "FLOAT",)
    RETURN_NAMES = ("style", "weight",)
    FS_CLASS_LABEL = "Style"

    def process_value(self, value, fallback_style = None, weight = None, **kwargs):
        weight_out = weight if weight is not None else 1

        if value is None:
            size = 512
            if fallback_style is not None:
                result = fallback_style
            else:
                result = torch.zeros([1, size // 8, size // 8, 3], device=self.device)
            weight_out = 0
        else:
            img_strs = value.split('.')
            try:
                all_imgs = [
                    img_from_base64(imgStr)
                    for imgStr in img_strs
                ]
                img0 = all_imgs[0]
            except Exception as e:
                raise ValueError(f"Could not read base64 image-data.\n{str(e)}")

            if len(all_imgs) < 1:
                print("Style input is only a single image")
                return img0, weight_out,

            img_rest = [
                comfy.utils.common_upscale(img.movedim(-1,1), img0.shape[2], img0.shape[1], "bilinear", "center").movedim(1,-1)
                if img0.shape[1:] != img.shape[1:]
                else img
                for img in all_imgs[1:]
            ]

            result = torch.cat([img0]+img_rest, dim=0)

        return result, weight_out,

    def value_required(self, **kwargs) -> bool:
        return False

    def fs_request_data(self, style_name: str | None = None, **kwargs):
        result = {}
        if style_name is not None and len(style_name) > 0:
            result["style"] = style_name
        return result

    def fs_response_test(self, response, **kwargs):
        if not isinstance(response, dict):
            raise Exception("response is not a dict")
        if not isinstance(response.get("style", ""), str):
            raise Exception("response.style is not a string")


    def fs_request_message_type(self, **kwargs):
        return "flyingshapes_request_style"


class InputScreenShot(FsInputNode):
    screenshot_types = ["default", "depth", "normal", "sketch", "mask"]

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "type": (s.screenshot_types,),
                "width": ("INT", {"default": 912, "min": 12, }),
                "height": ("INT", {"default": 512, "min": 12, }),
                "stored_value": ("STRING", {"default": empty_base64_image, }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("Screenshot (IMAGE)",)
    FS_CLASS_LABEL = "Image"

    def process_value(self, value, **kwargs):
        img = img_from_base64(value)
        # return (img, mask)
        return (img,)

    def fs_request_data(self, type=None, height=512, width=910, **kwargs):
        return {
            "type": type if type is not None else self.screenshot_types[0],
            "height": height,
            "width": width,
        }

    def fs_response_test(self, response, **kwargs):
        if not isinstance(response, dict):
            raise Exception("response is not a dict")
        type = response.get("type", "")
        if not isinstance(type in self.screenshot_types):
            raise Exception(f"response.type is {type}, but should be one of {self.screenshot_types}")

    def fs_request_message_type(self, **kwargs):
        return "flyingshapes_request_screenshot"


class InputSettings(FsInputNode):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "batch_size": ("INT", {"default": 3, "min": 1, }),
            },
        }

    async def receive_value(self, batch_size: int, **kwargs):
        return (batch_size,)

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("batch_size",)
    FS_CLASS_LABEL = "Settings"


class OutputImages:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "order": ("INT", {"default": 0, "min": 0, }),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True

    def save_images(self, images, **kwargs):
        num_of_images = images.shape[0]
        pbar = comfy.utils.ProgressBar(num_of_images)
        step = 0
        for image in images:
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            pbar.update_absolute(step, num_of_images, ("PNG", img, None))
            step += 1

        return {}

    @classmethod
    def IS_CHANGED(cls, images, **kwargs):
        return time.time()
