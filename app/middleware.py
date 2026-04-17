from .exceptions import BaseAppException

# middleware.py 的意义：全局异常守卫。
# 任何 view 或 service 抛出 BaseAppException 的子类，都会在这里被统一转成 JSON 响应。
# View 里只需要 raise，不用再写 try/except + return JsonResponse。


class AppExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
        except BaseAppException as exc:
            return exc.to_response()
        return response
