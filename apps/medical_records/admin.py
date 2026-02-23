from django.contrib import admin
from .models import MedicalRecord, Diagnosis, Prescription, PrescriptionItem, LabTest


class DiagnosisInline(admin.TabularInline):
    model = Diagnosis
    extra = 1


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 1


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'visit_date', 'chief_complaint')
    list_filter = ('visit_date', 'doctor')
    search_fields = ('patient__email', 'patient__first_name', 'chief_complaint')
    date_hierarchy = 'visit_date'
    inlines = [DiagnosisInline]


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'doctor', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('patient__email', 'patient__first_name')
    inlines = [PrescriptionItemInline]


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ('test_name', 'patient', 'doctor', 'status', 'is_abnormal')
    list_filter = ('status', 'is_abnormal', 'test_type')
    search_fields = ('test_name', 'patient__email')
