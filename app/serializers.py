import json

from app.careplans.models import CarePlanJob

# serializers.py 的意义：翻译官。把前端说的话（bytes/JSON）翻译成后端能用的格式（dict/对象），
# 把后端的结果（数据库对象）翻译成前端能看懂的格式（JSON dict）。


# -----------------------------
# Request parsing
# -----------------------------

def parse_request_body(body: bytes) -> dict:
    print("\n---------- [serializers.py] parse_request_body ----------")
    print(f"[serializers.py] 收到原始 bytes，开始解析...")
    result = json.loads(body.decode("utf-8"))
    print(f"[serializers.py] 解析完成，变成 dict: {result}")
    print("---------- [serializers.py] parse_request_body 结束 ----------\n")
    return result


# -----------------------------
# Response formatting
# -----------------------------

def serialize_order_created(provider, patient, order, job) -> dict:
    print("\n---------- [serializers.py] serialize_order_created ----------")
    print(f"[serializers.py] 收到 4 个 Model 对象，开始格式化...")
    result = {
        "provider_id": provider.id,
        "patient_id": patient.id,
        "order_id": order.id,
        "job_id": job.id,
        "status": job.status,
        "message": "Received",
    }
    print(f"[serializers.py] 格式化完成，变成 dict: {result}")
    print("---------- [serializers.py] serialize_order_created 结束 ----------\n")
    return result


def serialize_careplan(job: CarePlanJob) -> dict:
    return {
        "job_id": job.id,
        "order_id": job.order.id,
        "status": job.status,
        "care_plan_text": job.care_plan_text if job.status == CarePlanJob.STATUS_COMPLETED else "",
        "error": job.error_message if job.status == CarePlanJob.STATUS_FAILED else "",
        "updated_at": job.updated_at.isoformat(),
    }


def serialize_careplan_status(job: CarePlanJob) -> dict:
    return {
        "job_id": job.id,
        "status": job.status,
        "care_plan_text": job.care_plan_text if job.status == CarePlanJob.STATUS_COMPLETED else "",
        "error": job.error_message if job.status == CarePlanJob.STATUS_FAILED else "",
    }
