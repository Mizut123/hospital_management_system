"""
Views for user authentication and account management.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.db.models import Count, Q, F
from django.utils import timezone
from datetime import timedelta

from .models import User, Department, DoctorProfile, AuditLog
from .forms import LoginForm, UserRegistrationForm, UserProfileForm, AdminUserForm


def login_view(request):
    """Handle user login."""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Log the login action
            AuditLog.objects.create(
                user=user,
                action=AuditLog.Action.LOGIN,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

            # Remember me functionality
            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)

            messages.success(request, f'Welcome back, {user.first_name}!')
            return redirect('accounts:dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()

    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    """Handle user logout."""
    if request.user.is_authenticated:
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.LOGOUT,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('accounts:login')


def register_view(request):
    """Handle patient self-registration."""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.Role.PATIENT
            user.save()

            # Log the registration
            AuditLog.objects.create(
                user=user,
                action=AuditLog.Action.CREATE,
                model_name='User',
                object_id=str(user.id),
                object_repr=str(user),
            )

            login(request, user)
            messages.success(request, 'Registration successful! Welcome to the hospital management system.')
            return redirect('accounts:dashboard')
    else:
        form = UserRegistrationForm()

    return render(request, 'auth/register.html', {'form': form})


@login_required
def dashboard_view(request):
    """Route users to their role-specific dashboard."""
    user = request.user

    if user.is_admin:
        return redirect('accounts:admin_dashboard')
    elif user.is_doctor:
        return redirect('accounts:doctor_dashboard')
    elif user.is_receptionist:
        return redirect('accounts:receptionist_dashboard')
    elif user.is_pharmacist:
        return redirect('accounts:pharmacist_dashboard')
    else:
        return redirect('accounts:patient_dashboard')


@login_required
def patient_dashboard(request):
    """Dashboard for patients."""
    from apps.appointments.models import Appointment
    from apps.medical_records.models import MedicalRecord, Prescription

    user = request.user
    today = timezone.now().date()

    context = {
        'upcoming_appointments': Appointment.objects.filter(
            patient=user,
            scheduled_date__gte=today,
            status__in=['scheduled', 'confirmed']
        ).order_by('scheduled_date', 'scheduled_time')[:5],
        'recent_records': MedicalRecord.objects.filter(patient=user).order_by('-visit_date')[:5],
        'active_prescriptions': Prescription.objects.filter(
            patient=user,
            status='active'
        ).order_by('-created_at')[:5],
        'total_visits': MedicalRecord.objects.filter(patient=user).count(),
    }

    # Get AI health insights if available
    try:
        from apps.ai_services.services import get_patient_risk_score
        context['risk_score'] = get_patient_risk_score(user)
    except:
        context['risk_score'] = None

    return render(request, 'dashboards/patient.html', context)


@login_required
def doctor_dashboard(request):
    """Dashboard for doctors."""
    if not request.user.is_doctor:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    from apps.appointments.models import Appointment
    from apps.medical_records.models import MedicalRecord

    today = timezone.now().date()
    user = request.user

    # Today's appointments
    todays_appointments = Appointment.objects.filter(
        doctor=user,
        scheduled_date=today
    ).select_related('patient').order_by('queue_number', 'scheduled_time')

    context = {
        'todays_appointments': todays_appointments,
        'waiting_count': todays_appointments.filter(status='checked_in').count(),
        'completed_count': todays_appointments.filter(status='completed').count(),
        'total_today': todays_appointments.count(),
        'recent_patients': MedicalRecord.objects.filter(
            doctor=user
        ).select_related('patient').order_by('-visit_date')[:10],
        'pending_count': todays_appointments.filter(status__in=['scheduled', 'confirmed']).count(),
    }

    # Get workload optimization suggestions
    try:
        from apps.ai_services.services import get_workload_optimization
        context['workload_insights'] = get_workload_optimization(user)
    except:
        context['workload_insights'] = None

    return render(request, 'dashboards/doctor.html', context)


@login_required
def receptionist_dashboard(request):
    """Dashboard for receptionists."""
    if not request.user.is_receptionist:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    from apps.appointments.models import Appointment
    from apps.patients.models import Patient

    today = timezone.now().date()

    # Today's queue
    queue = Appointment.objects.filter(
        scheduled_date=today
    ).select_related('patient', 'doctor', 'department').order_by('queue_number', 'scheduled_time')

    context = {
        'queue': queue,
        'waiting_patients': queue.filter(status='checked_in').count(),
        'total_appointments': queue.count(),
        'completed': queue.filter(status='completed').count(),
        'new_registrations_today': User.objects.filter(
            role=User.Role.PATIENT,
            date_joined__date=today
        ).count(),
        'departments': Department.objects.filter(is_active=True),
    }

    # Get wait time estimations
    try:
        from apps.ai_services.services import get_queue_wait_times
        context['wait_times'] = get_queue_wait_times()
    except:
        context['wait_times'] = None

    return render(request, 'dashboards/receptionist.html', context)


@login_required
def pharmacist_dashboard(request):
    """Dashboard for pharmacists."""
    if not request.user.is_pharmacist:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    from apps.pharmacy.models import Medicine, MedicineStock
    from apps.medical_records.models import Prescription

    today = timezone.now().date()

    # Pending prescriptions
    pending_prescriptions = Prescription.objects.filter(
        status='pending'
    ).select_related('patient', 'doctor').order_by('-created_at')

    # Stock alerts
    low_stock = MedicineStock.objects.filter(
        quantity__lte=F('reorder_level')
    ).select_related('medicine')

    expiring_soon = MedicineStock.objects.filter(
        expiry_date__lte=today + timedelta(days=30),
        expiry_date__gt=today
    ).select_related('medicine')

    context = {
        'pending_prescriptions': pending_prescriptions[:20],
        'pending_count': pending_prescriptions.count(),
        'low_stock_items': low_stock[:10],
        'low_stock_count': low_stock.count(),
        'expiring_soon': expiring_soon[:10],
        'expiring_count': expiring_soon.count(),
        'dispensed_today': Prescription.objects.filter(
            status='dispensed',
            updated_at__date=today
        ).count(),
    }

    # Get stock predictions
    try:
        from apps.ai_services.services import get_stock_predictions
        context['stock_predictions'] = get_stock_predictions()
    except:
        context['stock_predictions'] = None

    return render(request, 'dashboards/pharmacist.html', context)


@login_required
def admin_dashboard(request):
    """Dashboard for administrators."""
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    from apps.appointments.models import Appointment
    from apps.medical_records.models import MedicalRecord

    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    # User statistics
    user_stats = User.objects.values('role').annotate(count=Count('id'))

    context = {
        'total_users': User.objects.count(),
        'user_stats': {stat['role']: stat['count'] for stat in user_stats},
        'total_departments': Department.objects.filter(is_active=True).count(),
        'appointments_today': Appointment.objects.filter(scheduled_date=today).count(),
        'appointments_week': Appointment.objects.filter(scheduled_date__gte=week_ago).count(),
        'new_patients_week': User.objects.filter(
            role=User.Role.PATIENT,
            date_joined__date__gte=week_ago
        ).count(),
        'recent_logs': AuditLog.objects.select_related('user')[:20],
        'active_doctors': User.objects.filter(role=User.Role.DOCTOR, is_active=True).count(),
    }

    # Get analytics
    try:
        from apps.ai_services.services import get_hospital_analytics
        context['analytics'] = get_hospital_analytics()
    except:
        context['analytics'] = None

    return render(request, 'dashboards/admin.html', context)


@login_required
def profile_view(request):
    """View and edit user profile."""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'accounts/profile.html', {'form': form})


# Admin views for user management
class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require admin role."""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin


class UserListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """List all users for admin management."""

    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        queryset = User.objects.all().order_by('-created_at')
        role = self.request.GET.get('role')
        search = self.request.GET.get('search')

        if role:
            queryset = queryset.filter(role=role)
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = User.Role.choices
        context['current_role'] = self.request.GET.get('role', '')
        context['search'] = self.request.GET.get('search', '')
        return context


class UserCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Create a new user."""

    model = User
    form_class = AdminUserForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def form_valid(self, form):
        messages.success(self.request, 'User created successfully.')
        return super().form_valid(form)


class UserUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Update an existing user."""

    model = User
    form_class = AdminUserForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def form_valid(self, form):
        messages.success(self.request, 'User updated successfully.')
        return super().form_valid(form)


class DepartmentListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """List all departments."""

    model = Department
    template_name = 'accounts/department_list.html'
    context_object_name = 'departments'


class AuditLogListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """View audit logs."""

    model = AuditLog
    template_name = 'accounts/audit_logs.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        queryset = AuditLog.objects.select_related('user').order_by('-timestamp')
        action = self.request.GET.get('action')
        user_id = self.request.GET.get('user')

        if action:
            queryset = queryset.filter(action=action)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset
