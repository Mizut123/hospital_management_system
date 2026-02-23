"""
URL patterns for appointments app.
"""
from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    path('book/', views.book_appointment, name='book'),
    path('book-for-patient/', views.book_for_patient, name='book_for_patient'),
    path('my/', views.MyAppointmentsView.as_view(), name='my_appointments'),
    path('<int:pk>/', views.AppointmentDetailView.as_view(), name='detail'),
    path('<int:pk>/check-in/', views.check_in, name='check_in'),
    path('<int:pk>/start/', views.start_consultation, name='start_consultation'),
    path('<int:pk>/cancel/', views.cancel_appointment, name='cancel'),
    path('queue/', views.queue_view, name='queue'),
    path('doctor-queue/', views.doctor_queue_view, name='doctor_queue'),
    path('schedule/', views.schedule_view, name='schedule'),
    path('api/slots/', views.get_available_slots, name='get_slots'),
]
