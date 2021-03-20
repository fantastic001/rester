

from rester import HttpClient

class WithBaseUrl(HttpClient):
    def __init__(self, http, baseurl):
        self.http = http
        self.baseurl = baseurl
    def send_request(self, url, method, data, headers):
        return self.http.send_request(self.baseurl + url, method, data, headers)