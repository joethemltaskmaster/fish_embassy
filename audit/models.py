from django.db import models


class AuditLog(models.Model):
    """Append-only log of service-level actions. Written by services, never edited."""
    action = models.CharField(max_length=60)
    target = models.CharField(max_length=120)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.action} → {self.target}"