from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()


class StaffCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    group = forms.ModelChoiceField(queryset=Group.objects.all(), required=False)
    is_superuser = forms.BooleanField(
        required=False,
        label="Grant Superuser Status",
        help_text="WARNING: Grants unrestricted system access."
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])

        is_super = self.cleaned_data.get("is_superuser")
        user.is_superuser = is_super
        user.is_staff = is_super

        if commit:
            user.save()
            group = self.cleaned_data.get("group")
            if group:
                user.groups.add(group)
        return user

