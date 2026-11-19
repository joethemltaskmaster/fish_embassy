from django import forms
from .models import OperatingExpense

class OperatingExpenseForm(forms.ModelForm):
    class Meta:
        model = OperatingExpense
        fields = ("date", "category", "amount", "description")
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }