"""
URL Configuration for Hospital Management System
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.accounts.urls', namespace='accounts')),
    path('patients/', include('apps.patients.urls', namespace='patients')),
    path('appointments/', include('apps.appointments.urls', namespace='appointments')),
    path('records/', include('apps.medical_records.urls', namespace='medical_records')),
    path('pharmacy/', include('apps.pharmacy.urls', namespace='pharmacy')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('analytics/', include('apps.analytics.urls', namespace='analytics')),
    path('ai/', include('apps.ai_services.urls', namespace='ai_services')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
