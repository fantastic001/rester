from rester import Operation
from rester.http_decorators import WithHeaders

class BearerAuthOperation(Operation):
    def __init__(self, auth_request, request, prefix="Bearer"):
        self.auth_request = auth_request
        self.request = request
        self.prefix = prefix
    
    def perform(self, http):
        self.auth_request.perform(http)
        result = self.auth_request.get_result()
        self.request.perform(WithHeaders(http, {
            "Authorization": "%s %s" % (self.prefix, result)
        }))