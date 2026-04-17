import logging

from .exceptions import BaseAppException, BlockError, WarningException

logger = logging.getLogger(__name__)

# middleware.py 的意义：全局异常守卫。
# 任何 view 或 service 抛出 BaseAppException 的子类，都会在这里被统一转成 JSON 响应。
# View 里只需要 raise，不用再写 try/except + return JsonResponse。
#
# 注意：必须用 process_exception 而不是在 __call__ 里 try/except。
# Django 内部用 convert_exception_to_response 在 view 层把异常转成 500，
# 那个转换发生在异常传播到 __call__ 的 try/except 之前，所以 try/except 捕不到。
# process_exception 是 Django 在转 500 之前专门留给 middleware 拦截异常的钩子。


class AppExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, WarningException):
            logger.warning("WarningException: code=%s message=%s", exception.code, exception.message)
            return exception.to_response()
        if isinstance(exception, BlockError):
            logger.error("BlockError: code=%s message=%s", exception.code, exception.message)
            return exception.to_response()
        if isinstance(exception, BaseAppException):
            logger.error("AppException: type=%s code=%s message=%s", exception.type, exception.code, exception.message)
            return exception.to_response()
        return None  # 其他异常交给 Django 默认处理
