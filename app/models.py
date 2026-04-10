from django.db import models


class Provider(models.Model):
    name = models.CharField(max_length=255)
    npi = models.CharField(max_length=32)  # 先不做唯一性/10位校验（后面再加）

    def __str__(self):
        return f"{self.name} ({self.npi})"


class Patient(models.Model):
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)
    mrn = models.CharField(max_length=32)  # 先不做唯一性/6位校验（后面再加）

    dob = models.DateField(null=True, blank=True)

    primary_diagnosis = models.CharField(max_length=64)  # ICD-10 code
    additional_diagnoses = models.JSONField(default=list, blank=True)  # list of ICD-10
    medication_history = models.JSONField(default=list, blank=True)    # list of strings

    def __str__(self):
        return f"{self.first_name} {self.last_name} (MRN {self.mrn})"


class Order(models.Model):
    """
    一个 care plan 对应一个订单（一种药物）
    """
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE)

    medication_name = models.CharField(max_length=255)

    # 先只支持纯文本（PDF 上传后面做）
    patient_records_text = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order#{self.id} - {self.patient} - {self.medication_name}"
