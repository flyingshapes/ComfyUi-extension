import typing
import asyncio
import re
import yaml
from os import path

#ReceiveTest = typing.Callable[[typing.Any], bool]
#ReceiveFilter: typing.TypeAlias = ReceiveTest | typing.FrozenSet[tuple[str, typing.Any]]
#ReceiveFilterOrDict: typing.TypeAlias = ReceiveFilter | typing.Dict[str, typing.Any]
#ReceiveFilter: typing.TypeAlias = ReceiveTest | str
#ReceiveMessageType: typing.TypeAlias = tuple[str, ReceiveFilter, asyncio.Future]

fs_sid_prefix = "flyingShapes"
fs_request_id_field = "__fs_requestId"

empty_base64_image = 'iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII='
empty_base64_red = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC='
empty_base64_green = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mNk+M9Qz0AEYBxVSF+FAAhKDveksOjmAAAAAElFTkSuQmCC='
empty_base64_blue = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mNkYPhfz0AEYBxVSF+FAP5FDvcfRYWgAAAAAElFTkSuQmCC='

def is_fs_id(id: str, *prefix: str) -> bool:
    return id.startswith('-'.join([
        fs_sid_prefix,
        *prefix
    ]))

def is_fs_web_id(id: str) -> bool:
    return is_fs_id(id, 'web')

def make_fs_id(id: str, *prefix: str) -> str:
    return '-'.join([
        fs_sid_prefix,
        *prefix,
        id
    ])


FlyingShapes_extra_data: typing.Dict[str, typing.Dict[str, typing.Any]] = {}

FlyingShapes_message_handlers: typing.Dict[str, asyncio.Future] = dict()


def to_snake_case(name: str) -> str:
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub('__([A-Z])', r'_\1', name)
    name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    return name  # .lower()

FsVersionYamlType = typing.Dict[str, typing.Dict[str, str]]
def_version_file = path.join(path.dirname(__file__), 'version.yml')
class FsVersionInfo:
    git_hash = "local"
    sem_ver = "1.0.0"
    data: typing.Dict[str, str] = {
        "git_hash": git_hash,
        "sem_ver": sem_ver,
    }
    @classmethod
    def load_version(cls, version_file: str = def_version_file):
        if path.isfile(version_file):
            with open(version_file) as stream:
                try:
                    content: FsVersionYamlType = yaml.safe_load(stream)
                    print(content)
                    fs_comfy_ui = content.get('fs_comfy_ui')
                    if fs_comfy_ui is None:
                        print(' missing fs_comfy_ui node in ' + version_file)
                    else:
                        cls.data = fs_comfy_ui
                        cls.git_hash = fs_comfy_ui.get('git_hash')
                        cls.sem_ver = fs_comfy_ui.get('sem_ver')

                except yaml.YAMLError as exc:
                    print(' could not read fs-version info')
                    print(exc)
        else:
            print(' file ' + version_file + ' not found')