"""
Patient-specific models for the Hospital Management System.
"""
from django.db import models
from django.conf import settings


class Patient(models.Model):
    """Extended patient information linked to User model."""

    BLOOD_GROUPS = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_profile'
    )
    patient_number = models.CharField(max_length=20, unique=True, blank=True)
    national_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text='National ID number for primary identification'
    )
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUPS, blank=True)
    allergies = models.TextField(blank=True, help_text='List of known allergies')
    chronic_conditions = models.TextField(blank=True, help_text='Existing chronic conditions')
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relation = models.CharField(max_length=50, blank=True)
    insurance_provider = models.CharField(max_length=100, blank=True)
    insurance_id = models.CharField(max_length=50, blank=True)
    risk_score = models.IntegerField(default=0, help_text='AI-calculated risk score 0-100')
    risk_level = models.CharField(max_length=20, default='low', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.patient_number})"

    def save(self, *args, **kwargs):
        if not self.patient_number:
            # Generate patient number
            last_patient = Patient.objects.order_by('-id').first()
            if last_patient and last_patient.patient_number:
                try:
                    num = int(last_patient.patient_number[3:]) + 1
                except ValueError:
                    num = 1
            else:
                num = 1
            self.patient_number = f"PAT{num:06d}"
        super().save(*args, **kwargs)


class PatientDocument(models.Model):
    """Documents uploaded by or for patients."""

    DOCUMENT_TYPES = [
        ('report', 'Medical Report'),
        ('scan', 'Scan/X-Ray'),
        ('prescription', 'Prescription'),
        ('insurance', 'Insurance Document'),
        ('other', 'Other'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=200)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='patient_documents/')
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} - {self.patient.user.get_full_name()}"
