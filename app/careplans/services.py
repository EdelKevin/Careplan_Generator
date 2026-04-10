from django.conf import settings
from django.utils import timezone

from .models import CarePlanJob


class LLMRetryableError(RuntimeError):
    """可重试的 LLM 错误（超时/5xx/限流等）"""
    pass


def call_llm_generate_care_plan(prompt: str) -> str:
    """
    TODO: 换成你真实 OpenAI 调用。
    先用占位实现跑通：输入含 FAIL 则触发可重试错误。
    """
    if "FAIL" in (prompt or ""):
        raise LLMRetryableError("Simulated LLM failure (for retry demo)")

    return (
        f"CARE PLAN @ {timezone.now().isoformat()}\n\n"
        f"Prompt:\n{prompt}\n"
    )


def build_stub_careplan(order) -> str:
    p = order.patient
    pr = order.provider

    return f"""Problem list / Drug therapy problems (DTPs)
- Need therapy optimization for {order.medication_name}
- Risk of adverse drug reactions
- Patient education / adherence considerations

Goals (SMART)
- Improve symptoms and functional status within 2 weeks
- No serious adverse events during therapy course
- Complete medication course with documented monitoring

Pharmacist interventions / plan
- Verify indication and appropriateness for {order.medication_name}
- Review medication history and potential interactions
- Provide patient counseling and written instructions
- Coordinate follow-up with provider ({pr.name}, NPI {pr.npi})

Monitoring plan
- Baseline vitals and relevant labs (as appropriate)
- Monitor for common adverse effects during therapy
- Document response and safety follow-up within 7-14 days

(Stub) Patient: {p.first_name} {p.last_name}, MRN {p.mrn}, Dx {p.primary_diagnosis}""".strip()


def llm_generate_careplan(order) -> str:
    if not getattr(settings, "OPENAI_API_KEY", ""):
        return build_stub_careplan(order)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        prompt = f"""
You are a clinical pharmacist.

Generate a care plan with EXACTLY these sections:
1) Problem list / Drug therapy problems (DTPs)
2) Goals (SMART)
3) Pharmacist interventions / plan
4) Monitoring plan

Patient:
- Name: {order.patient.first_name} {order.patient.last_name}
- MRN: {order.patient.mrn}
- Primary diagnosis: {order.patient.primary_diagnosis}
- Additional diagnoses: {order.patient.additional_diagnoses}
- Medication: {order.medication_name}
- Medication history: {order.patient.medication_history}

Provider:
- {order.provider.name}, NPI {order.provider.npi}

Clinical notes:
{order.patient_records_text}

Write concise, professional clinical English.
Use bullet points where appropriate.
""".strip()

        resp = client.chat.completions.create(
            model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "You are a clinical pharmacist generating care plans."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        return resp.choices[0].message.content

    except Exception:
        return build_stub_careplan(order)
