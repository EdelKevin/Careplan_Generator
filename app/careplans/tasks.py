from __future__ import annotations

from celery import shared_task
from django.db import transaction

from app.careplans.models import CarePlanJob
from app.careplans.services import LLMRetryableError, call_llm_generate_care_plan


@shared_task(
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_jitter=True,
    retry_backoff_max=60,
)
def generate_care_plan_task(self, job_id: int) -> None:

    # --- 1) 标记 PROCESSING（幂等：如果已 COMPLETED 就直接返回）---
    with transaction.atomic():
        job = CarePlanJob.objects.select_for_update().get(id=job_id)
        if job.status == CarePlanJob.STATUS_COMPLETED:
            return

        job.status = CarePlanJob.STATUS_PROCESSING
        job.error_message = ""
        job.save(update_fields=["status", "error_message", "updated_at"])

    try:
        # --- 2) 组装 prompt ---
        order = job.order
        prompt = f"""
        Patient: {getattr(order, "patient", "")}
        Provider: {getattr(order, "provider", "")}
        Medication: {getattr(order, "medication_name", "")}

        Patient Records:
        {getattr(order, "patient_records_text", "")}
        """.strip()

        # --- 3) 调 LLM ---
        care_plan = call_llm_generate_care_plan(prompt)

        # --- 4) 成功写回 ---
        with transaction.atomic():
            job = CarePlanJob.objects.select_for_update().get(id=job_id)
            job.care_plan_text = care_plan
            job.status = CarePlanJob.STATUS_COMPLETED
            job.save(update_fields=["care_plan_text", "status", "updated_at"])

    except LLMRetryableError as e:
        with transaction.atomic():
            job = CarePlanJob.objects.select_for_update().get(id=job_id)
            job.error_message = f"{type(e).__name__}: {e}"
            job.save(update_fields=["error_message", "updated_at"])

        if self.request.retries >= self.max_retries:
            with transaction.atomic():
                job = CarePlanJob.objects.select_for_update().get(id=job_id)
                job.status = CarePlanJob.STATUS_FAILED
                job.save(update_fields=["status", "updated_at"])
            return

        raise self.retry(exc=e)

    except Exception as e:
        with transaction.atomic():
            job = CarePlanJob.objects.select_for_update().get(id=job_id)
            job.status = CarePlanJob.STATUS_FAILED
            job.error_message = f"Unhandled {type(e).__name__}: {e}"
            job.save(update_fields=["status", "error_message", "updated_at"])
        raise
