from apps.common.models import ActivityLog

def log_activity(user, action, entity_type, entity_id, entity_name, summary, details=None):
    """
    Central helper to record audit activity history.
    Safely captures user snapshot, role, entity reference, and details.
    """
    user_name = "System"
    user_role = "SYSTEM"
    actual_user = None

    if user and hasattr(user, "is_authenticated") and user.is_authenticated:
        actual_user = user
        user_name = user.get_full_name() or user.username
        user_role = getattr(user, "role", "STAFF")

    return ActivityLog.objects.create(
        user=actual_user,
        user_name=user_name,
        user_role=user_role,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else "",
        entity_name=entity_name or "",
        summary=summary,
        details=details or {},
    )
