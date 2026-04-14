from django.db import transaction

from .models import Provider, Patient, Order
from app.careplans.models import CarePlanJob
from app.careplans.tasks import generate_care_plan_task

# services.py 的意义：真正干活的人。接到翻译好的数据之后，
# 负责写数据库、触发 Celery 任务。views 和 serializers 都不碰数据库，只有这里碰。


class ServiceError(Exception):
    """业务层抛出的错误，views 可以接住并返回给前端。"""
    pass


def create_order(data: dict):
    print("\n---------- [services.py] create_order ----------")
    print(f"[services.py] 收到 dict，开始写数据库...")

    with transaction.atomic():
        provider = Provider.objects.create(
            name=data.get("provider_name", ""),
            npi=data.get("provider_npi", ""),
        )
        print(f"[services.py] Provider 写入数据库，id={provider.id}, name={provider.name}")

        patient = Patient.objects.create(
            first_name=data.get("patient_first_name", ""),
            last_name=data.get("patient_last_name", ""),
            mrn=data.get("patient_mrn", ""),
            dob=data.get("dob") or None,
            primary_diagnosis=data.get("primary_diagnosis", ""),
            additional_diagnoses=data.get("additional_diagnoses", []) or [],
            medication_history=data.get("medication_history", []) or [],
        )
        print(f"[services.py] Patient 写入数据库，id={patient.id}, name={patient.first_name} {patient.last_name}")

        order = Order.objects.create(
            patient=patient,
            provider=provider,
            medication_name=data.get("medication_name", ""),
            patient_records_text=data.get("patient_records", ""),
        )
        print(f"[services.py] Order 写入数据库，id={order.id}, medication={order.medication_name}")

        job = CarePlanJob.objects.create(
            order=order,
            status=CarePlanJob.STATUS_PENDING,
        )
        print(f"[services.py] CarePlanJob 写入数据库，id={job.id}, status={job.status}")

        print(f"[services.py] 事务提交后，触发 Celery task，job_id={job.id}")
        transaction.on_commit(lambda: generate_care_plan_task.delay(job.id))

    print(f"[services.py] 返回 4 个 Model 对象给 views")
    print("---------- [services.py] create_order 结束 ----------\n")
    return provider, patient, order, job


def get_careplan_job(job_id: int) -> CarePlanJob:
    return CarePlanJob.objects.get(id=job_id)
