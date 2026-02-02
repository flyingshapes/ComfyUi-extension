from os import path
from typing import Dict, Optional
import yaml
from pydantic import BaseModel, ValidationError

class FsComfyUiConfig(BaseModel):
    sem_ver: str
    git_hash: Optional[str] = None
    git_clean: Optional[bool] = None
    config: Optional[str] = None
    build_type: Optional[str] = None
    ui_server: Optional[str] = None
    #env.str("FS_COMFY_UI_SERVER", None)) # configur8 None
    #dev: bool = False

class FsWebConfig(BaseModel):
    fs_web_servers: Dict[str, str] = {
        "prod": "https://api.flyingshapes.com",
        "staging": "https://api-staging.flyingshapes.com"
    }

class FsComfyConfig(BaseModel):
    fs_comfy_ui: FsComfyUiConfig
    fs_web: FsWebConfig = FsWebConfig()


def_version_file = path.join(path.dirname(__file__), 'version.yml')
def load_version(version_file: str = def_version_file):
    #return configur8.load(FsComfyConfig, version_file)
    with open(version_file, 'r') as stream:
        data = yaml.safe_load(stream)
    return FsComfyConfig.model_validate(data)



config = None

green = "\033[32m"
red = "\033[31m"
reset = "\033[0m"
bold = "\033[1m"

try:
    config = load_version()
    print(f"{bold}{green}✔ Successfully loaded Fs-comfy config. ✔{reset}")
except ValidationError as e:
    line_length = 100
    def expand_line(s: str, c = ""):
        s1 = f"⚠  {c}{s}  "
        # noinspection PyTypeChecker
        spaces = " " * (line_length - 6 - len(s))
        return f"{s1}{spaces}⚠{reset}"

    e_str = ""
    for el in str(e).split("\n"):
        el1 = expand_line(el, red)
        e_str += f"\n    {el1}"

    # noinspection PyTypeChecker
    warn_line = '⚠' * line_length
    first_line = expand_line(" Failed to load Fs-comfy config")
    banner = f"""
    {red}{warn_line}{reset}
    {first_line}{e_str}
    {red}{warn_line}{reset}
    """
    print(banner)