"""
Views for medical records management.
Security-enhanced with proper access control and audit logging.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.core.exceptions import PermissionDenied

from .models import MedicalRecord, Diagnosis, Prescription, PrescriptionItem, LabTest
from apps.appointments.models import Appointment
from apps.accounts.security import log_data_access, InputValidator

security_logger = logging.getLogger('security')


@login_required
@log_data_access('patient_medical_records')
def my_records(request):
    """View patient's own medical records."""
    records = MedicalRecord.objects.filter(
        patient=request.user
    ).select_related('doctor').prefetch_related('diagnoses', 'prescriptions')

    return render(request, 'medical_records/my_records.html', {'records': records})


@login_required
@log_data_access('patient_prescriptions')
def my_prescriptions(request):
    """View patient's prescriptions."""
    prescriptions = Prescription.objects.filter(
        patient=request.user
    ).select_related('doctor').prefetch_related('items__medicine')

    return render(request, 'medical_records/my_prescriptions.html', {'prescriptions': prescriptions})


@login_required
def doctor_records(request):
    """View records created by doctor."""
    if not request.user.is_doctor:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    records = MedicalRecord.objects.filter(
        doctor=request.user
    ).select_related('patient').prefetch_related('diagnoses')

    return render(request, 'medical_records/doctor_records.html', {'records': records})


class RecordDetailView(LoginRequiredMixin, DetailView):
    """View medical record details with access control."""

    model = MedicalRecord
    template_name = 'medical_records/detail.html'
    context_object_name = 'record'

    def get_object(self, queryset=None):
        """Override to add access control."""
        record = super().get_object(queryset)
        user = self.request.user

        # Access control: Only allow access to own records or if doctor/admin
        if not (user.is_admin or user.is_doctor or
                record.patient_id == user.id or
                (hasattr(user, 'patient') and record.patient_id == user.patient.id)):
            security_logger.warning(
                f"Unauthorized record access attempt: user={user.email}, record={record.pk}"
            )
            raise PermissionDenied("You don't have permission to view this record.")

        return record

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        record = self.object
        context['diagnoses'] = record.diagnoses.all()
        context['prescriptions'] = record.prescriptions.all()
        return context


@login_required
def create_record(request, appointment_id=None):
    """Create a new medical record (for doctors) with proper access control."""
    if not request.user.is_doctor:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    appointment = None
    if appointment_id:
        appointment = get_object_or_404(Appointment, pk=appointment_id)

        # SECURITY: Verify doctor is assigned to this appointment
        if appointment.doctor_id != request.user.id:
            security_logger.warning(
                f"Unauthorized appointment access: doctor={request.user.email}, "
                f"appointment={appointment_id}, assigned_doctor={appointment.doctor_id}"
            )
            messages.error(request, 'You are not assigned to this appointment.')
            return redirect('accounts:dashboard')

    if request.method == 'POST':
        patient_id = request.POST.get('patient') or (appointment.patient.id if appointment else None)

        record = MedicalRecord.objects.create(
            patient_id=patient_id,
            doctor=request.user,
            appointment=appointment,
            visit_date=timezone.now().date(),
            chief_complaint=request.POST.get('chief_complaint', ''),
            history_of_present_illness=request.POST.get('history', ''),
            vital_signs={
                'blood_pressure': request.POST.get('bp', ''),
                'pulse': request.POST.get('pulse', ''),
                'temperature': request.POST.get('temperature', ''),
                'weight': request.POST.get('weight', ''),
                'height': request.POST.get('height', ''),
            },
            physical_examination=request.POST.get('physical_exam', ''),
            assessment=request.POST.get('assessment', ''),
            plan=request.POST.get('plan', ''),
            notes=request.POST.get('notes', ''),
        )

        # Handle diagnoses
        diagnosis_descriptions = request.POST.getlist('diagnosis[]')
        for desc in diagnosis_descriptions:
            if desc.strip():
                Diagnosis.objects.create(
                    medical_record=record,
                    description=desc,
                )

        # Mark appointment as completed
        if appointment:
            appointment.complete()

        messages.success(request, 'Medical record created successfully.')
        return redirect('medical_records:detail', pk=record.pk)

    return render(request, 'medical_records/create.html', {
        'appointment': appointment,
        'patient': appointment.patient if appointment else None,
    })


@login_required
def create_prescription(request, record_id=None):
    """Create a prescription (for doctors) with access control."""
    if not request.user.is_doctor:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    record = None
    if record_id:
        record = get_object_or_404(MedicalRecord, pk=record_id)

        # SECURITY: Verify doctor created this record or is treating this patient
        if record.doctor_id != request.user.id:
            security_logger.warning(
                f"Unauthorized prescription attempt: doctor={request.user.email}, "
                f"record={record_id}, record_doctor={record.doctor_id}"
            )
            messages.error(request, 'You can only prescribe for your own patients.')
            return redirect('accounts:dashboard')

    if request.method == 'POST':
        from apps.pharmacy.models import Medicine

        prescription = Prescription.objects.create(
            patient_id=request.POST.get('patient') or record.patient.id,
            doctor=request.user,
            medical_record=record,
            notes=request.POST.get('notes', ''),
        )

        # Add prescription items
        medicine_ids = request.POST.getlist('medicine[]')
        dosages = request.POST.getlist('dosage[]')
        frequencies = request.POST.getlist('frequency[]')
        durations = request.POST.getlist('duration[]')
        quantities = request.POST.getlist('quantity[]')

        for i, med_id in enumerate(medicine_ids):
            if med_id:
                PrescriptionItem.objects.create(
                    prescription=prescription,
                    medicine_id=med_id,
                    dosage=dosages[i] if i < len(dosages) else '',
                    frequency=frequencies[i] if i < len(frequencies) else '',
                    duration=durations[i] if i < len(durations) else '',
                    quantity=int(quantities[i]) if i < len(quantities) and quantities[i] else 1,
                )

        messages.success(request, 'Prescription created successfully.')
        return redirect('medical_records:detail', pk=record.pk) if record else redirect('accounts:dashboard')

    from apps.pharmacy.models import Medicine, MedicineStock
    from django.db.models import Sum

    # Get medicines with stock information
    medicines = Medicine.objects.filter(is_active=True)

    # Build stock lookup dictionary
    stock_data = {}
    for medicine in medicines:
        total_stock = MedicineStock.objects.filter(
            medicine=medicine,
            quantity__gt=0
        ).aggregate(total=Sum('quantity'))['total'] or 0
        stock_data[medicine.pk] = {
            'available': total_stock,
            'status': 'in_stock' if total_stock > 10 else ('low_stock' if total_stock > 0 else 'out_of_stock')
        }

    return render(request, 'medical_records/create_prescription.html', {
        'record': record,
        'patient': record.patient if record else None,
        'medicines': medicines,
        'stock_data': stock_data,
    })


@login_required
@require_GET
def ai_diagnosis_api(request):
    """
    API endpoint for AI-powered diagnosis suggestions.
    Security: Role-restricted, input validated, rate limited via middleware.

    Query params:
        symptoms: Comma-separated list of symptoms (e.g., "fever,cough,headache")

    Returns:
        JSON with top 5 diagnosis suggestions including confidence scores and ICD codes.
    """
    if not request.user.is_doctor:
        security_logger.warning(
            f"Unauthorized AI diagnosis API access: user={request.user.email}"
        )
        return JsonResponse({'error': 'Access denied'}, status=403)

    symptoms_str = request.GET.get('symptoms', '')
    if not symptoms_str:
        return JsonResponse({'error': 'No symptoms provided'}, status=400)

    # SECURITY: Input validation - limit length and sanitize
    if len(symptoms_str) > 500:
        return JsonResponse({'error': 'Input too long'}, status=400)

    # Check for dangerous input patterns
    if InputValidator.contains_dangerous_input(symptoms_str):
        security_logger.warning(
            f"Dangerous input in AI diagnosis API: user={request.user.email}"
        )
        return JsonResponse({'error': 'Invalid input'}, status=400)

    # Parse and limit symptoms
    symptoms_list = [s.strip()[:50] for s in symptoms_str.split(',') if s.strip()][:20]

    # Get AI suggestions
    from apps.ai_services.services import get_ai_diagnosis_suggestions
    suggestions = get_ai_diagnosis_suggestions(symptoms_list)

    return JsonResponse({
        'symptoms_received': symptoms_list,
        'suggestions': suggestions,
        'disclaimer': 'AI suggestions are for reference only. Clinical judgment is required.',
    })


@login_required
@require_GET
def symptom_keywords_api(request):
    """
    API endpoint to get recognized symptom keywords for autocomplete.
    """
    from apps.ai_services.services import get_symptom_keywords
    keywords = get_symptom_keywords()

    return JsonResponse({
        'keywords': keywords,
    })
