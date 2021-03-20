
from rester import Operation
from rester.http_decorators import WithBaseUrl


class Sequence(Operation):
    def __init__(self, sequence, baseurl=""):
        self.sequence = sequence
        self.baseurl = baseurl
    
    def perform(self,http):
        for x in self.sequence:
            x.perform(WithBaseUrl(http, self.baseurl))
    def get_result(self):
        return list(x.get_result() for x in self.sequence)