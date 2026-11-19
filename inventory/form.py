from django import forms
from .models import Product, SKU, Location

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ("name", "description", "is_active")

class SKUForm(forms.ModelForm):
    class Meta:
        model = SKU
        fields = ("product", "code", "description", "unit_weight_kg", "base_unit", "selling_price", "is_active")

class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ("code", "name", "is_active")