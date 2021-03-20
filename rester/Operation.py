
from rester import HttpClient

class Operation:
    def perform(self, http: HttpClient):
        raise NotImplementedError()
    
    def get_result(self):
        return None