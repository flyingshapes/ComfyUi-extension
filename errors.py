import json
from aiohttp.web_exceptions import HTTPException
from typing import Any


class HTTPJsonResponse(HTTPException):
    def __init__(
            self,
            data: Any,
            status=400,
            #headers: Optional[LooseHeaders] = None,
            **kwargs
    ):
        self.status_code = status
        if isinstance(data, str):
            data = dict(error=data, **kwargs)
        elif isinstance(data, dict):
            data.update(**kwargs)

        text = json.dumps(data)
        super().__init__(
            content_type="application/json",
            text=text
        )