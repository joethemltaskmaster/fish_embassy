from django.db import models


class AuditLog(models.Model):
    action = models.CharField(max_length=60)
    target = models.CharField(max_length=120)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        permissions = [
            ("view_audit_history", "Can view audit history"),
        ]

    def get_natural_description(self):
        # Safely extract author info
        author_data = self.payload.get("author", {})
        author_name = author_data.get("name", "Unknown")
        author_role = author_data.get("role", "Unknown")

        author_str = f" (by {author_name} - {author_role})" if author_data else ""

        if self.action == "receive_stock":
            return f"Goods received. (Reference: {self.target}, Lines: {self.payload.get('line_count', 'N/A')}){author_str}"
        elif self.action == "sell_stock":
            return f"Sale recorded. (Reference: {self.target}, Total: ₦{self.payload.get('total', '0.00')}){author_str}"
        elif self.action == "staff_create":
            return f"Staff account created: {self.target}. Group: {self.payload.get('group', 'None')}. Superuser: {self.payload.get('is_superuser', False)}{author_str}"
        elif self.action == "record_expense":
            return f"Expense recorded: {self.target}. Amount: ₦{self.payload.get('amount', '0.00')}{author_str}"

        return f"System Action: {self.action} on {self.target}{author_str}"

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.action} → {self.target}"

