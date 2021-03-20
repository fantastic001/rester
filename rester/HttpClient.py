

import enum

class Method(enum.Enum):
    GET = 1 
    POST = 2 
    PUT = 3 
    DELETE = 4


class HttpClient:
    def send_request(self, url: str, method: Method, data: dict, headers: dict = None) -> object: 
        raise NotImplementedError()

