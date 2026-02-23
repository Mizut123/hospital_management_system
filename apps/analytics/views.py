"""
Views for analytics and reporting.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, F
from django.utils import timezone
from django.http import HttpResponse
from datetime import timedelta, datetime

from apps.accounts.models import User, Department
from apps.appointments.models import Appointment
from apps.medical_records.models import MedicalRecord, Prescription
from apps.pharmacy.models import Medicine, MedicineStock


@login_required
def analytics_dashboard(request):
    """Main analytics dashboard with enhanced AI insights."""
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Appointment statistics
    appointments_by_status = Appointment.objects.filter(
        scheduled_date__gte=month_ago
    ).values('status').annotate(count=Count('id'))

    appointments_by_dept = Appointment.objects.filter(
        scheduled_date__gte=month_ago
    ).values('department__name').annotate(count=Count('id'))

    # User statistics
    user_counts = User.objects.values('role').annotate(count=Count('id'))

    # Weekly trends
    daily_appointments = []
    for i in range(7):
        day = today - timedelta(days=i)
        count = Appointment.objects.filter(scheduled_date=day).count()
        daily_appointments.append({
            'date': day.strftime('%a'),
            'count': count
        })

    # Stock alerts
    low_stock_count = MedicineStock.objects.filter(
        quantity__lte=F('reorder_level'),
        quantity__gt=0
    ).count()
    out_of_stock_count = MedicineStock.objects.filter(quantity=0).count()

    # AI-powered insights
    try:
        from apps.ai_services.services import get_ml_stock_forecast, get_hospital_analytics
        stock_forecasts = get_ml_stock_forecast()[:5]
        ai_analytics = get_hospital_analytics()
    except Exception:
        stock_forecasts = []
        ai_analytics = None

    # Revenue estimate (based on completed appointments)
    completed_appointments = Appointment.objects.filter(
        scheduled_date__gte=month_ago,
        status='completed'
    ).count()
    estimated_revenue = completed_appointments * 50  # $50 avg consultation

    context = {
        'total_patients': User.objects.filter(role=User.Role.PATIENT).count(),
        'total_doctors': User.objects.filter(role=User.Role.DOCTOR).count(),
        'total_appointments_month': Appointment.objects.filter(scheduled_date__gte=month_ago).count(),
        'appointments_today': Appointment.objects.filter(scheduled_date=today).count(),
        'appointments_by_status': list(appointments_by_status),
        'appointments_by_dept': list(appointments_by_dept),
        'user_counts': {item['role']: item['count'] for item in user_counts},
        'daily_appointments': list(reversed(daily_appointments)),
        'prescriptions_month': Prescription.objects.filter(created_at__date__gte=month_ago).count(),
        'records_month': MedicalRecord.objects.filter(visit_date__gte=month_ago).count(),
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'stock_forecasts': stock_forecasts,
        'ai_analytics': ai_analytics,
        'estimated_revenue': estimated_revenue,
        'completed_appointments': completed_appointments,
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
