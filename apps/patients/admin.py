from django.contrib import admin
from .models import Patient, PatientDocument


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_number', 'get_full_name', 'blood_group', 'risk_level', 'created_at')
    list_filter = ('blood_group', 'risk_level')
    search_fields = ('patient_number', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('patient_number', 'risk_score', 'risk_level')

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Name'


@admin.register(PatientDocument)
class PatientDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'patient', 'document_type', 'uploaded_at')
    list_filter = ('document_type', 'uploaded_at')
    search_fields = ('title', 'patient__user__first_name', 'patient__user__last_name')
