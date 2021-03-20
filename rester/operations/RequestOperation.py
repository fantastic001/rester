
from rester import Operation 
from rester import HttpClient
from rester import Method 

class RequestOperation(Operation):
    def __init__(self, url: str, method: Method, data={}, headers=None):
        self.url = url 
        self.method = method 
        self.data = data
        self.headers = headers
    def perform(self, http: HttpClient):
        self.result = http.send_request(self.url, self.method, self.data, self.headers)
    
    def get_result(self):
        return self.result