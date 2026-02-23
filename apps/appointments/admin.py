from django.contrib import admin
from .models import Appointment, AppointmentSlot


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'scheduled_date', 'scheduled_time', 'status', 'queue_number')
    list_filter = ('status', 'appointment_type', 'scheduled_date', 'department')
    search_fields = ('patient__email', 'patient__first_name', 'doctor__first_name')
    date_hierarchy = 'scheduled_date'


@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'date', 'start_time', 'end_time', 'is_available', 'booked_count')
    list_filter = ('is_available', 'date')
