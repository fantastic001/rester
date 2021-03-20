
from rester import Operation


class Constant(Operation):
    def __init__(self, value):
        self.value = value
    
    def get_result(self):
        return self.value
    
    def perform(self, http):
        pass