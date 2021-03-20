
from unittest import TestCase 
from rester import HttpClient, Method 
from unittest import mock 

from rester import Operation
from rester.operations import RequestOperation
from rester import HttpClient

class TestBasic(TestCase):
    def setUp(self):
        self.http = HttpClient()
        self.http.send_request = mock.MagicMock(return_value="")

    def tearDown(self):
        print("Teardown")

    def test_operation_interface(self):
        self.assertRaises(NotImplementedError, Operation().perform, None)
    
    def test_http_request_get(self):
        self.assertTrue(issubclass(RequestOperation, Operation))
        x = RequestOperation("http://myurl/", Method.GET)
        x.perform(self.http)
        self.http.send_request.assert_called_with("http://myurl/", Method.GET, {})
    
    def test_http_request_post(self):
        RequestOperation("http://localhost/", Method.POST, {"data": 123}).perform(self.http)
        self.http.send_request.assert_called_with("http://localhost/", Method.POST, {"data": 123})
    
    def test_http_request_put(self):
        RequestOperation("http://localhost/", Method.PUT, "x").perform(self.http)
        self.http.send_request.assert_called_with("http://localhost/", Method.PUT, "x")
    
    def test_http_request_delete(self):
        RequestOperation("http://localhost/", Method.DELETE, {}).perform(self.http)
        self.http.send_request.assert_called_with("http://localhost/", Method.DELETE, {})
    
    def test_http_request_after_get_result_is_available(self):
        self.http.send_request = mock.MagicMock(return_value="xxx")
        x = RequestOperation("localhost", Method.GET)
        x.perform(self.http)
        self.assertEquals("xxx", x.get_result())
    