from django import forms
from inventory.models import SKU
from .models import Customer
from django.utils import timezone


class SellStockForm(forms.Form):
    customer = forms.ModelChoiceField(queryset=Customer.objects.filter(is_active=True))
    sku = forms.ModelChoiceField(queryset=SKU.objects.filter(is_active=True))
    qty = forms.DecimalField(min_value=0.001, max_digits=12, decimal_places=3, label="Quantity")
    reference = forms.CharField(required=False, max_length=100)
    idempotency_key = forms.CharField(widget=forms.HiddenInput)
    occurred_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        label="Transaction Date",
        initial=timezone.now  # <-- This populates it with today's date automatically
    )

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ("name", "phone", "email")