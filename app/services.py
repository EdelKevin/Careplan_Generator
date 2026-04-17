from django.db import transaction
from django.utils import timezone

from .models import Provider, Patient, Order
from app.careplans.models import CarePlanJob
from app.careplans.tasks import generate_care_plan_task
from .exceptions import BlockError, WarningException

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


def _check_patient(mrn: str, first_name: str, last_name: str, dob) -> Patient | None:
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

        raise WarningException(
            f"MRN {mrn} 已存在（Patient#{by_mrn.id}: {by_mrn.first_name} {by_mrn.last_name}, DOB {by_mrn.dob}），"
            f"但与传入的姓名或DOB不一致，请核实。",
            code="mrn_data_mismatch",
            hint="如确认要新建，请传入 confirm=true。",
        )

    if by_name_dob:
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
    print("\n---------- [services.py] create_order ----------")
    print(f"[services.py] 收到 dict，开始写数据库...")

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
            print(f"[services.py] Provider 新建，id={provider.id}, name={provider.name}")
        else:
            print(f"[services.py] Provider 复用，id={provider.id}, name={provider.name}")

        # --- Patient ---
        patient = _check_patient(mrn, first_name, last_name, dob)
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
            print(f"[services.py] Patient 新建，id={patient.id}, name={patient.first_name} {patient.last_name}")
        else:
            print(f"[services.py] Patient 复用，id={patient.id}, name={patient.first_name} {patient.last_name}")

        # --- Order ---
        _check_order(patient, medication, confirm)

        order = Order.objects.create(
            patient=patient,
            provider=provider,
            medication_name=medication,
            patient_records_text=data.get("patient_records", ""),
        )
        print(f"[services.py] Order 新建，id={order.id}, medication={order.medication_name}")

        job = CarePlanJob.objects.create(
            order=order,
            status=CarePlanJob.STATUS_PENDING,
        )
        print(f"[services.py] CarePlanJob 新建，id={job.id}, status={job.status}")

        print(f"[services.py] 事务提交后，触发 Celery task，job_id={job.id}")
        transaction.on_commit(lambda: generate_care_plan_task.delay(job.id))

    print(f"[services.py] 返回 4 个 Model 对象给 views")
    print("---------- [services.py] create_order 结束 ----------\n")
    return provider, patient, order, job


def get_careplan_job(job_id: int) -> CarePlanJob:
    return CarePlanJob.objects.get(id=job_id)
