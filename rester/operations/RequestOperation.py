
from rester import Operation 
from rester import HttpClient
from rester import Method 

class RequestOperation(Operation):
    def __init__(self, url: str, method: Method, data={}):
        self.url = url 
        self.method = method 
        self.data = data
    def perform(self, http: HttpClient):
        self.result = http.send_request(self.url, self.method, self.data)
    
    def get_result(self):
        return self.result