"""
Appointment and Queue Management Models.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class Appointment(models.Model):
    """Appointment model for scheduling patient visits."""

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        CONFIRMED = 'confirmed', 'Confirmed'
        CHECKED_IN = 'checked_in', 'Checked In'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        NO_SHOW = 'no_show', 'No Show'

    class AppointmentType(models.TextChoices):
        REGULAR = 'regular', 'Regular Consultation'
        FOLLOWUP = 'followup', 'Follow-up'
        EMERGENCY = 'emergency', 'Emergency'
        WALKIN = 'walkin', 'Walk-in'

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_appointments'
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctor_appointments'
    )
    department = models.ForeignKey(
        'accounts.Department',
        on_delete=models.SET_NULL,
        null=True
    )
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    appointment_type = models.CharField(
        max_length=20,
        choices=AppointmentType.choices,
        default=AppointmentType.REGULAR
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED
    )
    reason = models.TextField(blank=True, help_text='Reason for visit')
    notes = models.TextField(blank=True)

    # Queue management
    queue_number = models.IntegerField(null=True, blank=True)
    check_in_time = models.DateTimeField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    estimated_wait = models.IntegerField(null=True, blank=True, help_text='Estimated wait time in minutes')

    # AI-enhanced fields
    ai_priority = models.BooleanField(default=False, help_text='AI-flagged as priority case')
    ai_priority_reason = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_appointments'
    )

    class Meta:
        ordering = ['scheduled_date', 'scheduled_time']
        indexes = [
            models.Index(fields=['scheduled_date', 'doctor']),
            models.Index(fields=['patient', 'status']),
        ]

    def __str__(self):
        return f"{self.patient.get_full_name()} - Dr. {self.doctor.get_full_name()} ({self.scheduled_date})"

    def check_in(self):
        """Check in the patient."""
        self.status = self.Status.CHECKED_IN
        self.check_in_time = timezone.now()

        # Assign queue number
        today_appointments = Appointment.objects.filter(
            doctor=self.doctor,
            scheduled_date=self.scheduled_date,
            queue_number__isnull=False
        )
        max_queue = today_appointments.aggregate(models.Max('queue_number'))['queue_number__max'] or 0
        self.queue_number = max_queue + 1

        self.save()

    def start_consultation(self):
        """Mark consultation as started."""
        self.status = self.Status.IN_PROGRESS
        self.start_time = timezone.now()
        self.save()

    def complete(self):
        """Mark appointment as completed."""
        self.status = self.Status.COMPLETED
        self.end_time = timezone.now()
        self.save()


class AppointmentSlot(models.Model):
    """Available appointment slots for doctors."""

    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='appointment_slots'
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    max_patients = models.IntegerField(default=1)
    booked_count = models.IntegerField(default=0)

    class Meta:
        unique_together = ['doctor', 'date', 'start_time']
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"Dr. {self.doctor.get_full_name()} - {self.date} {self.start_time}"

    @property
    def is_fully_booked(self):
        return self.booked_count >= self.max_patients
