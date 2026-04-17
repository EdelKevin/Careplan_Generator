from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from . import serializers, services
from .exceptions import BlockError
from app.careplans.models import CarePlanJob

# views.py 的意义：前台接待员。负责接电话（收请求）、转给对应部门处理、
# 再把结果告诉打电话的人（返回响应）。自己不做任何实际工作。
#
# 错误处理约定：
#   - 业务异常（ValidationError / BlockError / WarningException）直接 raise，
#     由 AppExceptionMiddleware 统一转成 JSON，view 里不再写 try/except。
#   - 所有成功响应统一包装为 {"ok": true, "data": {...}}。


def home(request):
    return render(request, "index.html")


@csrf_exempt
def create_order(request):
    print("\n[urls.py] POST /api/orders/ 匹配到 → 交给 views.create_order")
    print("========== [views.py] create_order 被调用 ==========")
    print(f"[views.py] HTTP 方法: {request.method}")
    print(f"[views.py] 原始 body (bytes): {request.body[:100]}")

    if request.method != "POST":
        raise BlockError("POST only.", code="method_not_allowed", http_status=405)

    print("[views.py] 把 body 交给 serializers 解析...")
    data = serializers.parse_request_body(request.body)   # JSON 解析失败 → 抛 ValidationError
    print(f"[views.py] serializers 解析完毕，拿回 dict: {data}")

    confirm = data.get("confirm", False)

    print("[views.py] 把 dict 交给 services 处理...")
    provider, patient, order, job = services.create_order(data, confirm=confirm)
    print(f"[views.py] services 处理完毕，拿回 4 个对象")

    print("[views.py] 把对象交给 serializers 格式化成 JSON...")
    response_data = serializers.serialize_order_created(provider, patient, order, job)
    print(f"[views.py] 最终返回给前端: {response_data}")
    print("========== [views.py] 结束 ==========\n")

    return JsonResponse({"ok": True, "data": response_data}, status=202)


def get_careplan(_request, job_id: int):
    try:
        job = services.get_careplan_job(job_id)
    except CarePlanJob.DoesNotExist:
        raise BlockError("Care plan job not found.", code="not_found", http_status=404)

    return JsonResponse({"ok": True, "data": serializers.serialize_careplan(job)})


def careplan_status(_request, job_id: int):
    try:
        job = services.get_careplan_job(job_id)
    except CarePlanJob.DoesNotExist:
        raise BlockError("Care plan job not found.", code="not_found", http_status=404)

    return JsonResponse({"ok": True, "data": serializers.serialize_careplan_status(job)})


def download_careplan(_request, job_id: int):
    try:
        job = services.get_careplan_job(job_id)
    except CarePlanJob.DoesNotExist:
        raise BlockError("Care plan job not found.", code="not_found", http_status=404)

    if job.status != CarePlanJob.STATUS_COMPLETED:
        raise BlockError(
            f"Care plan not ready (status={job.status}).",
            code="not_ready",
            http_status=400,
        )

    content = job.care_plan_text or ""
    filename = f"careplan_job_{job.id}.txt"

    resp = HttpResponse(content, content_type="text/plain; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp
