from os import path
from typing import Dict, Optional, TypeVar
import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, Field
from pydantic.alias_generators import to_camel

class AppModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        serialize_by_alias=True,
        validate_by_alias=True,
        validate_by_name=True,
    )

class FsComfyUiVersionConfig(AppModel):
    sem_ver: str
    git_hash: Optional[str] = None
    git_clean: Optional[bool] = None
    config: Optional[str] = None
    build_type: Optional[str] = None
    ui_server: Optional[str] = None
    #env.str("FS_COMFY_UI_SERVER", None)) # configur8 None
    #dev: bool = False

class FsWebConfig(AppModel):
    fs_web_servers: Dict[str, str] = {
        "prod": "https://api.flyingshapes.com",
        "staging": "https://api-staging.flyingshapes.com"
    }

class FsComfyUser(AppModel):
    user_name: str
    password: str

class FsComfyUserConfig(AppModel):
    enabled: bool = False
    users: list[FsComfyUser] = []
    tokens: list[str] = []

class FsComfyConfig(AppModel):
    fs_comfy_ui: FsComfyUiVersionConfig
    fs_web: FsWebConfig = FsWebConfig()
    auth: FsComfyUserConfig = Field(default_factory=FsComfyUserConfig, exclude=True)


fs_ext_dir = path.dirname(__file__)


green = "\033[32m"
blue = "\033[34m"
red = "\033[31m"
reset = "\033[0m"
bold = "\033[1m"
line_length = 100


T = TypeVar("T", bound=BaseModel)
# noinspection PyPep8Naming
def load_config_file(conf_name: str, TypeCls: type[T], required: bool = False) -> T:
    conf_file = path.join(fs_ext_dir, f'{conf_name}.yml')
    if path.exists(conf_file):
        #conf_file
        with open(conf_file, 'r') as stream:
            data = yaml.safe_load(stream)

        try:
            result = TypeCls.model_validate(data, strict=True)
            print(f"{blue}[FS-Comfy]{reset} {bold}{green}✔ Successfully loaded Fs {conf_name} config. ✔{reset}")
            return result
        except ValidationError as e:
            def expand_line(s: str, c = ""):
                s1 = f"{red}⚠{reset}  {c}{s}  "
                # noinspection PyTypeChecker
                spaces = " " * (line_length - 6 - len(s))
                return f"{s1}{spaces}⚠{reset}"

            e_str = ""
            for el in str(e).split("\n"):
                el1 = expand_line(el, red)
                e_str += f"\n            {el1}"

            # noinspection PyTypeChecker
            warn_line = '⚠' * line_length
            first_line = expand_line(f" Failed to load Fs {conf_name} config")
            banner = f"""
            {red}{warn_line}{reset}
            {first_line}{e_str}
            {red}{warn_line}{reset}
            """
            print(banner)
            raise e
    elif required:
        raise FileNotFoundError(f"Config file '{conf_file}' not found.")
    else:
        return TypeCls()


fs_config: FsComfyConfig | None = None

def reload_config():
    global fs_config
    v_config = load_config_file('version', FsComfyUiVersionConfig, True)
    u_config = load_config_file('users', FsComfyUserConfig)

    if fs_config is None:
        fs_config = FsComfyConfig(
            fs_comfy_ui=v_config,
        )

    fs_config.fs_comfy_ui = v_config
    fs_config.auth = u_config

reload_config()
#print(f"{bold}{green}✔ Successfully loaded Fs-comfy config. ✔{reset}")