"""
Views for analytics and reporting.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, F, Avg, Q, ExpressionWrapper, DurationField
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from datetime import timedelta, datetime
import json

from apps.accounts.models import User, Department
from apps.appointments.models import Appointment
from apps.medical_records.models import MedicalRecord, Prescription
from apps.pharmacy.models import Medicine, MedicineStock, StockTransaction


@login_required
def analytics_dashboard(request):
    """Main analytics dashboard with detailed hospital insights."""
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    today = timezone.now().date()
    month_ago = today - timedelta(days=30)

    # ── Appointment statistics ──────────────────────────────────────────────
    appointments_by_status = Appointment.objects.filter(
        scheduled_date__gte=month_ago
    ).values('status').annotate(count=Count('id'))

    appointments_by_dept = Appointment.objects.filter(
        scheduled_date__gte=month_ago
    ).values('department__name').annotate(count=Count('id')).order_by('-count')

    # Daily appointments (last 30 days for trend chart)
    daily_appointments = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        count = Appointment.objects.filter(scheduled_date=day).count()
        daily_appointments.append({'date': day.strftime('%d %b'), 'count': count})

    # No-show & cancellation rates
    total_month = Appointment.objects.filter(scheduled_date__gte=month_ago).count()
    noshow_count = Appointment.objects.filter(scheduled_date__gte=month_ago, status='no_show').count()
    cancelled_count = Appointment.objects.filter(scheduled_date__gte=month_ago, status='cancelled').count()
    completed_count = Appointment.objects.filter(scheduled_date__gte=month_ago, status='completed').count()

    noshow_rate = round((noshow_count / total_month * 100) if total_month else 0, 1)
    cancel_rate = round((cancelled_count / total_month * 100) if total_month else 0, 1)
    completion_rate = round((completed_count / total_month * 100) if total_month else 0, 1)

    # ── Patient demographics ────────────────────────────────────────────────
    from apps.patients.models import Patient

    # Age groups (based on date_of_birth on User model)
    from django.db.models.functions import ExtractYear
    patients_qs = User.objects.filter(role=User.Role.PATIENT, date_of_birth__isnull=False)
    current_year = today.year
    age_groups = {'0-17': 0, '18-35': 0, '36-50': 0, '51-65': 0, '65+': 0}
    for u in patients_qs.values_list('date_of_birth', flat=True):
        age = current_year - u.year
        if age <= 17:
            age_groups['0-17'] += 1
        elif age <= 35:
            age_groups['18-35'] += 1
        elif age <= 50:
            age_groups['36-50'] += 1
        elif age <= 65:
            age_groups['51-65'] += 1
        else:
            age_groups['65+'] += 1

    # Gender breakdown
    gender_counts = User.objects.filter(role=User.Role.PATIENT).values('gender').annotate(count=Count('id'))

    # Blood group distribution
    blood_groups = Patient.objects.exclude(blood_group='').values('blood_group').annotate(count=Count('id')).order_by('blood_group')

    # Risk level breakdown
    risk_levels = Patient.objects.values('risk_level').annotate(count=Count('id'))

    # ── Doctor performance ──────────────────────────────────────────────────
    top_doctors = Appointment.objects.filter(
        scheduled_date__gte=month_ago,
        doctor__isnull=False
    ).values(
        'doctor__id', 'doctor__first_name', 'doctor__last_name'
    ).annotate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
    ).order_by('-total')[:8]

    for d in top_doctors:
        d['completion_rate'] = round((d['completed'] / d['total'] * 100) if d['total'] else 0, 1)
        d['name'] = f"Dr. {d['doctor__first_name']} {d['doctor__last_name']}"

    # ── Most prescribed medicines (from prescriptions) ──────────────────────
    from apps.medical_records.models import PrescriptionItem
    top_medicines = PrescriptionItem.objects.values(
        'medicine__name'
    ).annotate(count=Count('id')).order_by('-count')[:10]

    # ── Stock alerts ────────────────────────────────────────────────────────
    low_stock_count = MedicineStock.objects.filter(quantity__lte=F('reorder_level'), quantity__gt=0).count()
    out_of_stock_count = MedicineStock.objects.filter(quantity=0).count()

    # ── AI-powered insights ──────────────────────────────────────────────────
    try:
        from apps.ai_services.services import get_ml_stock_forecast, get_hospital_analytics
        stock_forecasts = get_ml_stock_forecast()[:5]
        ai_analytics = get_hospital_analytics()
    except Exception:
        stock_forecasts = []
        ai_analytics = None

    # ── User statistics ─────────────────────────────────────────────────────
    user_counts = {item['role']: item['count']
                   for item in User.objects.values('role').annotate(count=Count('id'))}

    context = {
        # Totals
        'total_patients': User.objects.filter(role=User.Role.PATIENT).count(),
        'total_doctors': User.objects.filter(role=User.Role.DOCTOR).count(),
        'total_appointments_month': total_month,
        'appointments_today': Appointment.objects.filter(scheduled_date=today).count(),
        # Appointment breakdown
        'appointments_by_status': list(appointments_by_status),
        'appointments_by_dept': list(appointments_by_dept),
        'daily_appointments': daily_appointments,
        'daily_appointments_json': json.dumps([d['count'] for d in daily_appointments]),
        'daily_labels_json': json.dumps([d['date'] for d in daily_appointments]),
        # Rates
        'noshow_rate': noshow_rate,
        'cancel_rate': cancel_rate,
        'completion_rate': completion_rate,
        'noshow_count': noshow_count,
        'cancelled_count': cancelled_count,
        'completed_count': completed_count,
        # Demographics
        'age_groups': age_groups,
        'age_groups_json': json.dumps(list(age_groups.values())),
        'gender_counts': list(gender_counts),
        'blood_groups': list(blood_groups),
        'blood_groups_json': json.dumps([{'label': b['blood_group'], 'count': b['count']} for b in blood_groups]),
        'risk_levels': list(risk_levels),
        # Doctor performance
        'top_doctors': list(top_doctors),
        # Pharmacy/records
        'prescriptions_month': Prescription.objects.filter(created_at__date__gte=month_ago).count(),
        'records_month': MedicalRecord.objects.filter(visit_date__gte=month_ago).count(),
        'top_medicines': list(top_medicines),
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        # AI
        'stock_forecasts': stock_forecasts,
        'ai_analytics': ai_analytics,
        # User distribution
        'user_counts': user_counts,
    }

    return render(request, 'analytics/dashboard.html', context)


@login_required
def reports(request):
    """Generate and download reports page."""
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    return render(request, 'analytics/reports.html')


@login_required
def download_report(request, report_type):
    """Download a generated report in PDF or Excel format."""
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    format = request.GET.get('format', 'pdf')
    date_from = request.GET.get('from')
    date_to = request.GET.get('to')

    # Parse dates
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        except ValueError:
            date_from = None
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            date_to = None

    try:
        from .services import ReportGenerator
        generator = ReportGenerator()

        if report_type == 'patients':
            buffer = generator.generate_patient_report(format=format, date_from=date_from, date_to=date_to)
            filename = f"patient_report_{timezone.now().strftime('%Y%m%d')}"
        elif report_type == 'appointments':
            buffer = generator.generate_appointment_report(format=format, date_from=date_from, date_to=date_to)
            filename = f"appointment_report_{timezone.now().strftime('%Y%m%d')}"
        elif report_type == 'pharmacy':
            buffer = generator.generate_pharmacy_report(format=format, date_from=date_from, date_to=date_to)
            filename = f"pharmacy_report_{timezone.now().strftime('%Y%m%d')}"
        elif report_type == 'doctor-activity':
            buffer = generator.generate_doctor_activity_report(format=format, date_from=date_from, date_to=date_to)
            filename = f"doctor_activity_report_{timezone.now().strftime('%Y%m%d')}"
        else:
            messages.error(request, 'Invalid report type.')
            return redirect('analytics:reports')

        if format == 'pdf':
            content_type = 'application/pdf'
            filename += '.pdf'
        else:
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename += '.xlsx'

        response = HttpResponse(buffer.read(), content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except ImportError as e:
        messages.error(request, f'Report generation failed: {str(e)}')
        return redirect('analytics:reports')
    except Exception as e:
        messages.error(request, f'Error generating report: {str(e)}')
        return redirect('analytics:reports')


@login_required
def stock_forecast_view(request):
    """View ML-powered stock forecasts."""
    if not request.user.is_admin and not request.user.is_pharmacist:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    try:
        from apps.ai_services.services import get_ml_stock_forecast
        forecasts = get_ml_stock_forecast()
    except Exception:
        forecasts = []

    return render(request, 'analytics/stock_forecast.html', {
        'forecasts': forecasts,
    })
