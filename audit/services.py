from .models import AuditLog


def record(action: str, target: str, payload: dict | None = None) -> AuditLog:
    return AuditLog.objects.create(action=action, target=target, payload=payload or {})