"""
Medical Records Models - EHR, Diagnoses, Prescriptions, Lab Tests.
"""
from django.db import models
from django.conf import settings


class MedicalRecord(models.Model):
    """Electronic Health Record for a patient visit."""

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='medical_records'
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='doctor_records'
    )
    appointment = models.OneToOneField(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_record'
    )
    visit_date = models.DateField()
    chief_complaint = models.TextField(help_text='Primary reason for visit')
    history_of_present_illness = models.TextField(blank=True)
    vital_signs = models.JSONField(default=dict, blank=True, help_text='BP, Pulse, Temp, etc.')
    physical_examination = models.TextField(blank=True)
    assessment = models.TextField(blank=True)
    plan = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-visit_date', '-created_at']

    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.visit_date}"


class Diagnosis(models.Model):
    """Diagnosis linked to a medical record."""

    SEVERITY_CHOICES = [
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
        ('critical', 'Critical'),
    ]

    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='diagnoses')
    icd_code = models.CharField(max_length=20, blank=True, help_text='ICD-10 Code')
    description = models.CharField(max_length=500)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='mild')
    notes = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Diagnoses'

    def __str__(self):
        return f"{self.icd_code} - {self.description}"


class Prescription(models.Model):
    """Prescription issued to a patient."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        DISPENSED = 'dispensed', 'Dispensed'
        PARTIALLY_DISPENSED = 'partial', 'Partially Dispensed'
        CANCELLED = 'cancelled', 'Cancelled'

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prescriptions'
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='issued_prescriptions'
    )
    medical_record = models.ForeignKey(
        MedicalRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prescriptions'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    dispensed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispensed_prescriptions'
    )
    dispensed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Rx-{self.pk} - {self.patient.get_full_name()}"


class PrescriptionItem(models.Model):
    """Individual medicine in a prescription."""

    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey('pharmacy.Medicine', on_delete=models.CASCADE)
    dosage = models.CharField(max_length=100, help_text='e.g., 500mg')
    frequency = models.CharField(max_length=100, help_text='e.g., Twice daily')
    duration = models.CharField(max_length=100, help_text='e.g., 7 days')
    quantity = models.IntegerField(default=1)
    instructions = models.TextField(blank=True, help_text='Special instructions')
    is_dispensed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.medicine.name} - {self.dosage}"


class LabTest(models.Model):
    """Laboratory test ordered for a patient."""

    class Status(models.TextChoices):
        ORDERED = 'ordered', 'Ordered'
        SAMPLE_COLLECTED = 'collected', 'Sample Collected'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lab_tests'
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ordered_tests'
    )
    medical_record = models.ForeignKey(
        MedicalRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    test_name = models.CharField(max_length=200)
    test_type = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ORDERED)
    results = models.JSONField(default=dict, blank=True)
    result_summary = models.TextField(blank=True)
    is_abnormal = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    ordered_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-ordered_at']

    def __str__(self):
        return f"{self.test_name} - {self.patient.get_full_name()}"
