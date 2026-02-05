from django.utils.decorators import decorator_from_middleware
from django.middleware.clickjacking import XFrameOptionsMiddleware

class AllowIframeMiddleware(XFrameOptionsMiddleware):
    def process_response(self, request, response):
        response['X-Frame-Options'] = 'ALLOWALL'
        return response

allow_iframe = decorator_from_middleware(AllowIframeMiddleware)
