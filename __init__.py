from .nodes import *
from .common import *
# noinspection PyUnresolvedReferences
from . import routes
# noinspection PyUnresolvedReferences
from . import login

FS_PREFIX = "FLYINGSHAPES_"


def node_class_map_name(cls):
    return FS_PREFIX + to_snake_case(cls.__name__)


print("Loading Flyingshapes")

All_Fs_Nodes = [
    InputSlider,
    InputText,
    InputScreenShot,
    InputStyle,
    InputSettings,
    OutputImages
]

NODE_CLASS_MAPPINGS = {
    node_class_map_name(cls): cls
    for cls in All_Fs_Nodes
}

NODE_DISPLAY_NAME_MAPPINGS = {
    node_class_map_name(cls): ("FS " + getattr(cls, "FS_CLASS_LABEL", cls.__name__))
    for cls in All_Fs_Nodes
}

# For loading all custom js
WEB_DIRECTORY = "js"
