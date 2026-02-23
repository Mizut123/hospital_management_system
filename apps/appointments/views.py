"""
Views for appointment management.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime, timedelta

from apps.accounts.models import User, Department
from .models import Appointment, AppointmentSlot


@login_required
def book_appointment(request):
    """Book an appointment (for patients)."""
    departments = Department.objects.filter(is_active=True)
    doctors = User.objects.filter(role=User.Role.DOCTOR, is_active=True)

    if request.method == 'POST':
        doctor_id = request.POST.get('doctor')
        date = request.POST.get('date')
        time = request.POST.get('time')
        reason = request.POST.get('reason', '')

        doctor = get_object_or_404(User, pk=doctor_id, role=User.Role.DOCTOR)

        appointment = Appointment.objects.create(
            patient=request.user,
            doctor=doctor,
            department=doctor.doctor_profile.department if hasattr(doctor, 'doctor_profile') else None,
            scheduled_date=date,
            scheduled_time=time,
            reason=reason,
            created_by=request.user,
        )

        messages.success(request, 'Appointment booked successfully!')
        return redirect('appointments:detail', pk=appointment.pk)

    return render(request, 'appointments/book.html', {
        'departments': departments,
        'doctors': doctors,
    })


@login_required
def book_for_patient(request):
    """Book appointment for a patient (for receptionists)."""
    if not (request.user.is_receptionist or request.user.is_admin):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    departments = Department.objects.filter(is_active=True)
    doctors = User.objects.filter(role=User.Role.DOCTOR, is_active=True)

    if request.method == 'POST':
        patient_id = request.POST.get('patient')
        doctor_id = request.POST.get('doctor')
        date = request.POST.get('date')
        time = request.POST.get('time')
        reason = request.POST.get('reason', '')
        appointment_type = request.POST.get('appointment_type', 'regular')

        patient = get_object_or_404(User, pk=patient_id, role=User.Role.PATIENT)
        doctor = get_object_or_404(User, pk=doctor_id, role=User.Role.DOCTOR)

        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            department=doctor.doctor_profile.department if hasattr(doctor, 'doctor_profile') else None,
            scheduled_date=date,
            scheduled_time=time,
            reason=reason,
            appointment_type=appointment_type,
            created_by=request.user,
        )

        messages.success(request, f'Appointment booked for {patient.get_full_name()}!')
        return redirect('appointments:queue')

    return render(request, 'appointments/book_for_patient.html', {
        'departments': departments,
        'doctors': doctors,
    })


class MyAppointmentsView(LoginRequiredMixin, ListView):
    """View patient's appointments."""

    model = Appointment
    template_name = 'appointments/my_appointments.html'
    context_object_name = 'appointments'
    paginate_by = 10

    def get_queryset(self):
        return Appointment.objects.filter(
            patient=self.request.user
        ).select_related('doctor', 'department').order_by('-scheduled_date', '-scheduled_time')


class AppointmentDetailView(LoginRequiredMixin, DetailView):
    """View appointment details."""

    model = Appointment
    template_name = 'appointments/detail.html'
    context_object_name = 'appointment'


@login_required
def queue_view(request):
    """View and manage the appointment queue (for receptionists)."""
    if not (request.user.is_receptionist or request.user.is_admin):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    today = timezone.now().date()
    queue = Appointment.objects.filter(
        scheduled_date=today
    ).select_related('patient', 'doctor', 'department').order_by('queue_number', 'scheduled_time')

    return render(request, 'appointments/queue.html', {
        'queue': queue,
        'today': today,
    })


@login_required
def doctor_queue_view(request):
    """View doctor's patient queue."""
    if not request.user.is_doctor:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    today = timezone.now().date()
    queue = Appointment.objects.filter(
        doctor=request.user,
        scheduled_date=today
    ).select_related('patient', 'department').order_by('queue_number', 'scheduled_time')

    return render(request, 'appointments/doctor_queue.html', {
        'queue': queue,
        'today': today,
    })


@login_required
def check_in(request, pk):
    """Check in a patient."""
    appointment = get_object_or_404(Appointment, pk=pk)

    if not (request.user.is_receptionist or request.user.is_admin):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    appointment.check_in()

    # Calculate estimated wait time using AI
    try:
        from apps.ai_services.services import calculate_wait_time
        appointment.estimated_wait = calculate_wait_time(appointment)
        appointment.save()
    except:
        pass

    messages.success(request, f'{appointment.patient.get_full_name()} checked in. Queue number: {appointment.queue_number}')
    return redirect('appointments:queue')


@login_required
def start_consultation(request, pk):
    """Start consultation with patient."""
    appointment = get_object_or_404(Appointment, pk=pk)

    if request.user != appointment.doctor:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    appointment.start_consultation()
    messages.success(request, f'Consultation started with {appointment.patient.get_full_name()}')
    return redirect('medical_records:create', appointment_id=pk)


@login_required
def cancel_appointment(request, pk):
    """Cancel an appointment."""
    appointment = get_object_or_404(Appointment, pk=pk)

    # Check permissions
    if not (request.user == appointment.patient or request.user.is_receptionist or request.user.is_admin):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    appointment.status = Appointment.Status.CANCELLED
    appointment.save()

    messages.success(request, 'Appointment cancelled successfully.')
    return redirect('appointments:my_appointments')


@login_required
def schedule_view(request):
    """View doctor's schedule."""
    if not request.user.is_doctor:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    # Get next 7 days of appointments
    today = timezone.now().date()
    week_ahead = today + timedelta(days=7)

    appointments = Appointment.objects.filter(
        doctor=request.user,
        scheduled_date__gte=today,
        scheduled_date__lte=week_ahead
    ).select_related('patient', 'department').order_by('scheduled_date', 'scheduled_time')

    return render(request, 'appointments/schedule.html', {
        'appointments': appointments,
        'today': today,
    })


@login_required
def get_available_slots(request):
    """API endpoint to get available slots for a doctor on a date."""
    doctor_id = request.GET.get('doctor')
    date = request.GET.get('date')

    if not doctor_id or not date:
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    # Get booked slots
    booked_times = Appointment.objects.filter(
        doctor_id=doctor_id,
        scheduled_date=date,
        status__in=['scheduled', 'confirmed', 'checked_in', 'in_progress']
    ).values_list('scheduled_time', flat=True)

    # Generate available time slots (9 AM to 5 PM, 30 min intervals)
    slots = []
    start = datetime.strptime('09:00', '%H:%M')
    end = datetime.strptime('17:00', '%H:%M')
    current = start

    while current < end:
        time_str = current.strftime('%H:%M')
        if datetime.strptime(time_str, '%H:%M').time() not in booked_times:
            slots.append(time_str)
        current += timedelta(minutes=30)

    return JsonResponse({'slots': slots})
