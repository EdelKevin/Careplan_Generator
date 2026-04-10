from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from . import serializers, services
from app.careplans.models import CarePlanJob

# views.py 的意义：前台接待员。负责接电话（收请求）、转给对应部门处理、
# 再把结果告诉打电话的人（返回响应）。自己不做任何实际工作。


def home(request):
    return render(request, "index.html")


@csrf_exempt
def create_order(request):
    print("\n[urls.py] POST /api/orders/ 匹配到 → 交给 views.create_order")
    print("========== [views.py] create_order 被调用 ==========")
    print(f"[views.py] HTTP 方法: {request.method}")
    print(f"[views.py] 原始 body (bytes): {request.body[:100]}")  # 只打印前100个字符

    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        print("[views.py] 把 body 交给 serializers 解析...")
        data = serializers.parse_request_body(request.body)
        print(f"[views.py] serializers 解析完毕，拿回 dict: {data}")
    except Exception:
        return JsonResponse({"error": "invalid json"}, status=400)

    print("[views.py] 把 dict 交给 services 处理...")
    provider, patient, order, job = services.create_order(data)
    print(f"[views.py] services 处理完毕，拿回 4 个对象: provider={provider}, patient={patient}, order={order}, job={job}")

    print("[views.py] 把对象交给 serializers 格式化成 JSON...")
    response_data = serializers.serialize_order_created(provider, patient, order, job)
    print(f"[views.py] 最终返回给前端: {response_data}")
    print("========== [views.py] 结束 ==========\n")

    return JsonResponse(response_data, status=202)


def get_careplan(request, job_id: int):
    try:
        job = services.get_careplan_job(job_id)
    except CarePlanJob.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    return JsonResponse(serializers.serialize_careplan(job))


def careplan_status(_request, job_id: int):
    try:
        job = services.get_careplan_job(job_id)
    except CarePlanJob.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    return JsonResponse(serializers.serialize_careplan_status(job))


def download_careplan(request, job_id: int):
    try:
        job = services.get_careplan_job(job_id)
    except CarePlanJob.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    if job.status != CarePlanJob.STATUS_COMPLETED:
        return JsonResponse({"error": f"not ready, status={job.status}"}, status=400)

    content = job.care_plan_text or ""
    filename = f"careplan_job_{job.id}.txt"

    resp = HttpResponse(content, content_type="text/plain; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp
