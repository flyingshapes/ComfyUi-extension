import typing
import asyncio
import re

ReceiveTest = typing.Callable[[typing.Any], bool]
ReceiveFilter: typing.TypeAlias = ReceiveTest | typing.FrozenSet[tuple[str, typing.Any]]
ReceiveFilterOrDict: typing.TypeAlias = ReceiveFilter | typing.Dict[str, typing.Any]
ReceiveMessageType: typing.TypeAlias = tuple[str, ReceiveFilter, asyncio.Future]

fs_sid_prefix = "flyingShapes"

empty_base64_image = 'iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII='
empty_base64_red = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC='
empty_base64_green = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mNk+M9Qz0AEYBxVSF+FAAhKDveksOjmAAAAAElFTkSuQmCC='
empty_base64_blue = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mNkYPhfz0AEYBxVSF+FAP5FDvcfRYWgAAAAAElFTkSuQmCC='

def is_fs_id(id: str) -> bool:
    return id.startswith(fs_sid_prefix)


def make_fs_id(id: str, *prefix: str) -> str:
    return '-'.join([
        fs_sid_prefix,
        *prefix,
        id
    ])


FlyingShapes_extra_data: typing.Dict[str, typing.Dict[str, typing.Any]] = {}

FlyingShapes_message_handlers: typing.Dict[str, typing.Set[tuple[ReceiveFilter, asyncio.Future]]] = dict()


def to_snake_case(name: str) -> str:
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub('__([A-Z])', r'_\1', name)
    name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    return name  # .lower()
