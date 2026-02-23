"""
Context processors for notifications.
"""

def notifications(request):
    """Add notification data to template context."""
    if request.user.is_authenticated:
        from .models import Notification
        recent = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]

        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        return {
            'recent_notifications': recent,
            'unread_notifications_count': unread_count,
        }
    return {}
