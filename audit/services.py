from .models import AuditLog

def record(action: str, target: str, payload: dict = None, user=None, service: str = "", component: str = "") -> AuditLog:
    """
    Records a business event.
    Automatically attaches the authenticated author and orchestrating service.
    """
    payload = payload or {}

    # 1. Capture Author (Snapshot name and role for historical accuracy)
    if user and getattr(user, 'is_authenticated', False):
        # Determine role
        if user.is_superuser:
            role = "Superuser"
        elif user.groups.exists():
            role = user.groups.first().name
        else:
            role = "Staff"

        author = {
            "id": user.id,
            "name": user.get_full_name() or user.username,
            "role": role,
            "type": "user"
        }
    else:
        author = {
            "id": None,
            "name": "System",
            "role": "System",
            "type": "system"
        }

    # 2. Capture Orchestrating Component
    orchestrated_by = {
        "service": service,
        "component": component
    }

    # 3. Merge into existing payload
    payload["author"] = author
    if service:
        payload["orchestrated_by"] = orchestrated_by

    # 4. Persist
    return AuditLog.objects.create(action=action, target=target, payload=payload)