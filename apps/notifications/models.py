"""
Notification system models.
"""
from django.db import models
from django.conf import settings


class Notification(models.Model):
    """User notifications."""

    class NotificationType(models.TextChoices):
        APPOINTMENT = 'appointment', 'Appointment'
        PRESCRIPTION = 'prescription', 'Prescription'
        LAB_RESULT = 'lab_result', 'Lab Result'
        REMINDER = 'reminder', 'Reminder'
        ALERT = 'alert', 'Alert'
        SYSTEM = 'system', 'System'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.get_full_name()}"

    def get_absolute_url(self):
        if self.link:
            return self.link
        return '#'

    def mark_as_read(self):
        self.is_read = True
        self.save()
