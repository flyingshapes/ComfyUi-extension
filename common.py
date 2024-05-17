import typing
import asyncio
import re

ReceiveFilter: typing.TypeAlias = typing.Callable[[typing.Any], bool] | typing.FrozenSet[tuple[str, typing.Any]]
ReceiveFilterOrDict: typing.TypeAlias = ReceiveFilter | typing.Dict[str, typing.Any]
ReceiveMessageType: typing.TypeAlias = tuple[str, ReceiveFilter, asyncio.Future]

fs_sid_prefix = "flyingShapes-"

FlyingShapes_extra_data: typing.Dict[str, typing.Dict[str, typing.Any]] = {}

FlyingShapes_message_handlers: typing.Dict[str, typing.Set[tuple[ReceiveFilter, asyncio.Future]]] = dict()


def to_snake_case(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub('__([A-Z])', r'_\1', name)
    name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    return name  # .lower()
