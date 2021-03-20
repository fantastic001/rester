

from rester import HttpClient

class WithHeaders(HttpClient):
    def __init__(self, http, headers):
        self.headers = headers
        self.http = http
    def send_request(self, url, method, data, headers=None):
        if headers is None:
            headers = self.headers
        self.http.send_request(url, method, data, headers)