from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
 
from portfolio_ai.ratelimit import rate_limit
 
 
class RateLimitDecoratorTests(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
 
    def make_view(self, **kwargs):
        @rate_limit('test', **kwargs)
        def view(request):
            return HttpResponse('ok')
        return view
 
    def test_requests_under_the_limit_all_succeed(self):
        view = self.make_view(limit=3, window=60)
        request = self.factory.get('/')
        for _ in range(3):
            response = view(request)
            self.assertEqual(response.status_code, 200)
 
    def test_request_over_the_limit_is_blocked_with_429(self):
        view = self.make_view(limit=3, window=60)
        request = self.factory.get('/')
        for _ in range(3):
            view(request)
        response = view(request)
        self.assertEqual(response.status_code, 429)
 
    def test_different_ips_are_tracked_independently(self):
        view = self.make_view(limit=1, window=60)
        request_a = self.factory.get('/', REMOTE_ADDR='1.1.1.1')
        request_b = self.factory.get('/', REMOTE_ADDR='2.2.2.2')
        self.assertEqual(view(request_a).status_code, 200)
        self.assertEqual(view(request_b).status_code, 200)
        # A second request from the SAME ip should now be blocked
        self.assertEqual(view(request_a).status_code, 429)
 
    def test_custom_key_func_is_used_for_identity(self):
        view = self.make_view(limit=1, window=60, key_func=lambda r: r.META.get('HTTP_X_USER_ID'))
        request_1 = self.factory.get('/', HTTP_X_USER_ID='user-1')
        request_2 = self.factory.get('/', HTTP_X_USER_ID='user-2')
        self.assertEqual(view(request_1).status_code, 200)
        self.assertEqual(view(request_2).status_code, 200)  # different key_func identity
        self.assertEqual(view(request_1).status_code, 429)  # same identity as request_1
 
    def test_x_forwarded_for_is_used_when_present(self):
        view = self.make_view(limit=1, window=60)
        request = self.factory.get('/', REMOTE_ADDR='10.0.0.1', HTTP_X_FORWARDED_FOR='203.0.113.5, 10.0.0.1')
        self.assertEqual(view(request).status_code, 200)
        # Same X-Forwarded-For value again should hit the same bucket and be blocked
        request2 = self.factory.get('/', REMOTE_ADDR='10.0.0.2', HTTP_X_FORWARDED_FOR='203.0.113.5, 10.0.0.2')
        self.assertEqual(view(request2).status_code, 429)
 
    def test_different_key_prefixes_do_not_share_a_bucket(self):
        @rate_limit('prefix-a', limit=1, window=60)
        def view_a(request):
            return HttpResponse('a')
 
        @rate_limit('prefix-b', limit=1, window=60)
        def view_b(request):
            return HttpResponse('b')
 
        request = self.factory.get('/')
        self.assertEqual(view_a(request).status_code, 200)
        # Different prefix, same client -> should NOT be blocked by view_a's usage
        self.assertEqual(view_b(request).status_code, 200)
 
    def test_view_return_value_is_passed_through_when_not_limited(self):
        view = self.make_view(limit=5, window=60)
        request = self.factory.get('/')
        response = view(request)
        self.assertEqual(response.content, b'ok')