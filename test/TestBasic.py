
from unittest import TestCase 
from rester import HttpClient, Method 
from unittest import mock 

from rester import Operation
from rester.operations import RequestOperation, BearerAuthOperation, Constant, Sequence
from rester import HttpClient
from rester.http_decorators import * 

class TestBasic(TestCase):
    def setUp(self):
        self.http = HttpClient()
        self.http.send_request = mock.MagicMock(return_value="")

    def tearDown(self):
        pass

    def test_operation_interface(self):
        self.assertRaises(NotImplementedError, Operation().perform, None)
    
    def test_http_request_get(self):
        self.assertTrue(issubclass(RequestOperation, Operation))
        x = RequestOperation("http://myurl/", Method.GET)
        x.perform(self.http)
        self.http.send_request.assert_called_with("http://myurl/", Method.GET, {}, None)
    
    def test_http_request_post(self):
        RequestOperation("http://localhost/", Method.POST, {"data": 123}).perform(self.http)
        self.http.send_request.assert_called_with("http://localhost/", Method.POST, {"data": 123}, None)
    
    def test_http_request_put(self):
        RequestOperation("http://localhost/", Method.PUT, "x").perform(self.http)
        self.http.send_request.assert_called_with("http://localhost/", Method.PUT, "x", None)
    
    def test_http_request_delete(self):
        RequestOperation("http://localhost/", Method.DELETE, {}).perform(self.http)
        self.http.send_request.assert_called_with("http://localhost/", Method.DELETE, {}, None)
    
    def test_http_request_after_get_result_is_available(self):
        self.http.send_request = mock.MagicMock(return_value="xxx")
        x = RequestOperation("localhost", Method.GET)
        x.perform(self.http)
        self.assertEqual("xxx", x.get_result())
    
    def test_http_request_with_headers(self):
        RequestOperation("www.google.com", Method.GET, {}, {"Content-Type": "application/json"}).perform(self.http)
        self.http.send_request.assert_called_with("www.google.com", Method.GET, {}, {"Content-Type": "application/json"})
    
    def test_constant(self):
        x = Constant("some string")
        x.perform(self.http)
        self.assertEqual(x.get_result(), "some string")


    def test_bearer_http_auth(self):
        auth = BearerAuthOperation(Constant("token"), RequestOperation("localhost", Method.GET))
        auth.perform(self.http)
        self.http.send_request.assert_called_with("localhost", Method.GET, {}, {"Authorization": "Bearer token"})

    def test_bearer_http_auth_sequence(self):
        auth = BearerAuthOperation(Constant("token"), Sequence([RequestOperation("http://localhost", Method.GET, {}, None)]))
        auth.perform(self.http)
        self.http.send_request.assert_called_with("http://localhost", Method.GET, {}, {
            "Authorization": "Bearer token"
        })

    def test_bearer_http_auth_custom_prefix(self):
        auth = BearerAuthOperation(Constant("token"), Sequence([RequestOperation("http://localhost", Method.GET, {}, None)]), "JWT")
        auth.perform(self.http)
        self.http.send_request.assert_called_with("http://localhost", Method.GET, {}, {
            "Authorization": "JWT token"
        })

    def test_bearer_request_sequence(self):
        s = Sequence([
            RequestOperation("/a/", Method.GET),
            RequestOperation("/a/", Method.GET),
            RequestOperation("/a/", Method.GET)
        ], "http://localhost")
        self.http.send_request = mock.MagicMock(return_value="x")
        s.perform(self.http)
        self.assertEqual(len(s.get_result()), 3)
        self.assertSequenceEqual(s.get_result(), ["x", "x", "x"])
        self.http.send_request.assert_called_with("http://localhost/a/", Method.GET, {}, None)
    

    def test_http_decorators_with_baseurl(self):
        WithBaseUrl(self.http, "http://localhost").send_request("/a/", Method.GET, {}, None)
        self.http.send_request.assert_called_with("http://localhost/a/", Method.GET, {}, None)
    def test_http_decorators_with_headers(self):
        WithHeaders(self.http, {
            "A": "B"
        }).send_request("http://localhost/a/", Method.GET, {},None)


        self.http.send_request.assert_called_with("http://localhost/a/", Method.GET, {}, {
            "A": "B"
        })