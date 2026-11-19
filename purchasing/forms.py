from datetime import date
from django import forms
from inventory.models import SKU, Location
from .models import Supplier

class ReceiveStockForm(forms.Form):
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.filter(is_active=True))
    sku = forms.ModelChoiceField(queryset=SKU.objects.filter(is_active=True))
    location = forms.ModelChoiceField(queryset=Location.objects.filter(is_active=True))
    qty = forms.DecimalField(min_value=0.001, max_digits=12, decimal_places=3, label="Quantity")
    unit_cost = forms.DecimalField(min_value=0, max_digits=14, decimal_places=2, label="Unit Cost (₦)")
    expiry_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    reference = forms.CharField(required=False, max_length=100, help_text="Optional PO or invoice number.")

    def clean_expiry_date(self):
        d = self.cleaned_data['expiry_date']
        if d < date.today():
            raise forms.ValidationError("Expiry date cannot be in the past.")
        return d

    def clean_qty(self):
        qty = self.cleaned_data['qty']
        if qty <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")
        return qty

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ("name", "phone", "email", "is_active")