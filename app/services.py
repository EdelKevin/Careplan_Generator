import logging

from django.db import transaction
from django.utils import timezone

from .models import Provider, Patient, Order
from app.careplans.models import CarePlanJob
from app.careplans.tasks import generate_care_plan_task
from .exceptions import BlockError, WarningException

logger = logging.getLogger(__name__)

# services.py 的意义：真正干活的人。接到翻译好的数据之后，
# 负责写数据库、触发 Celery 任务。views 和 serializers 都不碰数据库，只有这里碰。


# -----------------------------
# Duplicate detection helpers
# -----------------------------

def _check_provider(npi: str, name: str) -> Provider | None:
    existing = Provider.objects.filter(npi=npi).first()
    if not existing:
        return None

    if existing.name == name:
        return existing  # 完全一致，复用

    raise BlockError(
        f"NPI {npi} 已存在，绑定名字是 '{existing.name}'，"
        f"与传入的 '{name}' 不一致。NPI 是全国唯一执照号，不能重复。",
        code="npi_name_conflict",
    )


def _check_patient(mrn: str, first_name: str, last_name: str, dob, confirm: bool) -> Patient | None:
    by_mrn = Patient.objects.filter(mrn=mrn).first()
    by_name_dob = (
        Patient.objects.filter(first_name=first_name, last_name=last_name, dob=dob).first()
        if dob else None
    )

    if by_mrn:
        name_match = by_mrn.first_name == first_name and by_mrn.last_name == last_name
        dob_match = str(by_mrn.dob) == str(dob)

        if name_match and dob_match:
            return by_mrn  # 完全一致，复用

        if confirm:
            return by_mrn  # 用户已确认，复用现有 Patient

        raise WarningException(
            f"MRN {mrn} 已存在（Patient#{by_mrn.id}: {by_mrn.first_name} {by_mrn.last_name}, DOB {by_mrn.dob}），"
            f"但与传入的姓名或DOB不一致，请核实。",
            code="mrn_data_mismatch",
            hint="如确认要新建，请传入 confirm=true。",
        )

    if by_name_dob:
        if confirm:
            return None  # 用户已确认，用新 MRN 新建 Patient

        raise WarningException(
            f"患者 {first_name} {last_name}（DOB {dob}）已存在（Patient#{by_name_dob.id}），"
            f"但 MRN 不同：已有 {by_name_dob.mrn}，传入 {mrn}，请核实。",
            code="name_dob_mrn_mismatch",
            hint="如确认要新建，请传入 confirm=true。",
        )

    return None


def _check_order(patient: Patient, medication_name: str, confirm: bool) -> None:
    today = timezone.now().date()

    same_day = Order.objects.filter(
        patient=patient,
        medication_name=medication_name,
        created_at__date=today,
    ).first()

    if same_day:
        raise BlockError(
            f"今天已为 {patient} 创建过 {medication_name} 的处方（Order#{same_day.id}），不能重复创建。",
            code="duplicate_order_today",
        )

    if not confirm:
        previous = Order.objects.filter(
            patient=patient,
            medication_name=medication_name,
        ).first()

        if previous:
            raise WarningException(
                f"{patient} 之前已有 {medication_name} 的处方（Order#{previous.id}，{previous.created_at.date()}）。",
                code="duplicate_order_history",
                hint="如确认要新建，请传入 confirm=true。",
            )


# -----------------------------
# Order & job operations
# -----------------------------

def create_order(data: dict, confirm: bool = False):
    npi        = data.get("provider_npi", "")
    name       = data.get("provider_name", "")
    mrn        = data.get("patient_mrn", "")
    first_name = data.get("patient_first_name", "")
    last_name  = data.get("patient_last_name", "")
    dob        = data.get("dob") or None
    medication = data.get("medication_name", "")

    with transaction.atomic():

        # --- Provider ---
        provider = _check_provider(npi, name)
        if provider is None:
            provider = Provider.objects.create(name=name, npi=npi)
            logger.info("Provider created: id=%s name=%s", provider.id, provider.name)
        else:
            logger.info("Provider reused: id=%s name=%s", provider.id, provider.name)

        # --- Patient ---
        patient = _check_patient(mrn, first_name, last_name, dob, confirm)
        if patient is None:
            patient = Patient.objects.create(
                first_name=first_name,
                last_name=last_name,
                mrn=mrn,
                dob=dob,
                primary_diagnosis=data.get("primary_diagnosis", ""),
                additional_diagnoses=data.get("additional_diagnoses", []) or [],
                medication_history=data.get("medication_history", []) or [],
            )
            logger.info("Patient created: id=%s name=%s %s", patient.id, patient.first_name, patient.last_name)
        else:
            logger.info("Patient reused: id=%s name=%s %s", patient.id, patient.first_name, patient.last_name)

        # --- Order ---
        _check_order(patient, medication, confirm)

        order = Order.objects.create(
            patient=patient,
            provider=provider,
            medication_name=medication,
            patient_records_text=data.get("patient_records", ""),
        )
        logger.info("Order created: id=%s medication=%s", order.id, order.medication_name)

        job = CarePlanJob.objects.create(
            order=order,
            status=CarePlanJob.STATUS_PENDING,
        )
        logger.info("CarePlanJob created: id=%s status=%s", job.id, job.status)

        transaction.on_commit(lambda: generate_care_plan_task.delay(job.id))
        logger.info("Celery task queued: job_id=%s", job.id)

    return provider, patient, order, job


def get_careplan_job(job_id: int) -> CarePlanJob:
    return CarePlanJob.objects.get(id=job_id)
