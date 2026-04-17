from django.http import JsonResponse

# exceptions.py 的意义：定义项目里所有"不正常"情况的统一格式。
# 每种异常知道自己该被翻译成什么 HTTP 响应，middleware 只负责调 to_response()。
#
# 响应格式约定：
#   错误（ValidationError / BlockError）：
#     {"ok": false, "error": {"type": "...", "code": "...", "message": "...", "detail": ...}}
#
#   警告（WarningException）—— 操作未执行，需用户确认后重试：
#     {"ok": false, "warnings": [{"code": "...", "message": "...", "hint": "..."}]}
#
#   成功（由 view 直接返回）：
#     {"ok": true, "data": {...}}


class BaseAppException(Exception):
    """所有业务异常的基类。子类覆盖 type / default_code / http_status。"""

    type: str = "app_error"
    default_code: str = "error"
    default_message: str = "An error occurred."
    http_status: int = 500

    def __init__(
        self,
        message: str = None,
        *,
        code: str = None,
        detail=None,
        http_status: int = None,
    ):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.detail = detail
        if http_status is not None:
            self.http_status = http_status
        super().__init__(self.message)

    def to_response(self) -> JsonResponse:
        body: dict = {
            "ok": False,
            "error": {
                "type": self.type,
                "code": self.code,
                "message": self.message,
            },
        }
        if self.detail is not None:
            body["error"]["detail"] = self.detail
        return JsonResponse(body, status=self.http_status)


# -----------------------------
# 三个具体子类
# -----------------------------

class ValidationError(BaseAppException):
    """输入格式不合法（NPI 不是 10 位、MRN 不是 6 位等）→ 400。
    由 serializer 层抛出。
    """
    type = "validation_error"
    default_code = "invalid_input"
    default_message = "Input validation failed."
    http_status = 400


class BlockError(BaseAppException):
    """业务规则阻止操作（同 NPI 对应不同 Provider、同天重复开单）→ 409。
    由 service 层抛出。
    """
    type = "block_error"
    default_code = "blocked"
    default_message = "Operation blocked by a business rule."
    http_status = 409


class WarningException(BaseAppException):
    """可能存在问题，但允许用户确认后继续（疑似重复患者）→ 200。
    由 service 层抛出。前端收到后展示警告，用户确认则带 confirm=true 重试。
    """
    type = "warning"
    default_code = "warning"
    default_message = "Operation requires confirmation."
    http_status = 200

    def __init__(self, message: str = None, *, code: str = None, hint: str = None, detail=None):
        super().__init__(message, code=code, detail=detail)
        self.hint = hint

    def to_response(self) -> JsonResponse:
        warning: dict = {"code": self.code, "message": self.message}
        if self.hint:
            warning["hint"] = self.hint
        if self.detail is not None:
            warning["detail"] = self.detail
        return JsonResponse({"ok": False, "warnings": [warning]}, status=self.http_status)


# -----------------------------
# DRF 兼容（可选，未来引入 DRF 时取消注释）
# -----------------------------
# try:
#     from rest_framework.exceptions import ValidationError as DRFValidationError
#     _DRF_AVAILABLE = True
# except ImportError:
#     _DRF_AVAILABLE = False
#
# 在 AppExceptionMiddleware 里额外 catch DRFValidationError，转成 ValidationError.to_response()。
