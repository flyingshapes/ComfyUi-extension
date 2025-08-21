from typing import Any, Callable, Dict, Tuple, Type, TypeVar, Self
from .errors import HTTPJsonResponse
from aiohttp.web_request import Request

T = TypeVar("T")
Validator = Callable[[T, str], bool | str]

TypeSpec = (
        Type[T] |
        Tuple[Type[T], ...] |
        Tuple[Type[T], str] |
        Tuple[Type[T], Validator[T]] |
        Tuple[Type[T], str, Validator[T]]
)
ParsedTypeSpec = Tuple[
    Type[T],
    str,
    Validator[T] | None,
    str | None,
]

def parse_type_spec(spec: TypeSpec[T], key: str | None = None) -> ParsedTypeSpec[T]:
    typ: Type[T]
    pretty_name: str | None = None
    validator: Validator[T] | None = None

    if isinstance(spec, tuple):
        if len(spec) == 1:
            typ = spec[0]
        elif len(spec) == 2:
            if isinstance(spec[1], str):
                typ, pretty_name = spec  # (type, str)
            else:
                typ, validator = spec  # (type, callable)
            # leave pretty_name default if callable
        elif len(spec) == 3:
            typ, pretty_name, validator = spec
        else:
            add = "" if key is None else f" for '{key}'"
            raise ValueError(f"Invalid spec{add}: {spec}")
    else:
        typ = spec

    pretty_name_f = f"{pretty_name} ({key})" if pretty_name is not None else key

    return typ, pretty_name_f, validator, pretty_name

def parse_spec(spec: Dict[str, TypeSpec]) -> Dict[str, ParsedTypeSpec]:
    parsed: Dict[str, ParsedTypeSpec] = {}
    for key, type_spec in spec.items():
        parsed[key] = parse_type_spec(type_spec, key)
    return parsed

# def validate_input_single(data: Any, key: str, spec: TypeSpec[T]):
#     validate_impl(data, key, *parse_type_spec(spec, key))

_sentinel = object()

def validate_exists(data: Any, key: str, default: Any = _sentinel) -> Tuple[Any, bool]:
    if key not in data:
        if default is not _sentinel:
            return default, False
        raise HTTPJsonResponse(f"Missing required field '{key}'")

    return data[key], True


def validate_impl(
        data: Dict[str, Any],
        key: str,
        typ: Type[T],
        pretty_name_f: str,
        validator: Validator[T] | None,
        pretty_name: str | None,
        default: Any = _sentinel,
) -> T:
    value, existed = validate_exists(data, key, default)
    if not existed:
        return value

    # Type check
    if not isinstance(value, typ):
        raise HTTPJsonResponse(
            f"Field '{pretty_name_f}' expected type {getattr(typ, '__name__', typ)}, "
            f"got {type(value).__name__}"
        )

    valid: bool | str = validator is None or validator(value, key)
    if not valid:
        reason = f": {valid}" if isinstance(valid, str) else ""
        raise HTTPJsonResponse(f"Field '{pretty_name}' validation failed{reason}")

    return value

# def validate_input(data: dict[str, Any], spec: Dict[str, TypeSpec]) -> Dict[str, Any]:
#     """
#     Validate dict `data` against `spec`.
#     Raises HTTPJsonResponse if validation fails.
#     Returns the validated dict if all checks pass.
#     """
#
#     if not isinstance(data, dict):
#         raise HTTPJsonResponse(f"Expected a dict, got {type(data).__name__}")
#
#     for key, type_def in spec.items():
#         validate_input_single(data, key, type_def)
#
#     return data

class Validation:
    data: Dict[str, Any]

    def __init__(
            self,
            data: Dict,
            **spec: TypeSpec
    ):
        self.data = data
        self.spec = parse_spec(spec)

    @classmethod
    async def get(cls, request: Request, **spec: Dict[str, TypeSpec]) -> Self:
        json_data = await request.json()
        if not isinstance(json_data, dict):
            raise HTTPJsonResponse(f"Expected a dict, got {type(json_data).__name__}")

        return cls(json_data, **spec)


    def validate_any(self, key: str, default: Any = _sentinel) -> Any:
        return validate_exists(self.data, key, default)[0]

    def validate(self, key: str, spec: TypeSpec[T], default: Any = _sentinel) -> T:
        p_spec = parse_type_spec(spec, key)
        return validate_impl(self.data, key, *p_spec, default=default)

