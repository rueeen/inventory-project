from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Equipment, Supply, Request


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = [
            "inventory_code",
            "name",
            "detailed_spec",
            "academic_area",
            "careers",
            "subjects",
            "storage_location",
            "condition",
            "unit_value_uf",
            "observations",
        ]
        widgets = {
            "detailed_spec": forms.Textarea(attrs={"rows": 3}),
            "observations": forms.Textarea(attrs={"rows": 3}),
            "careers": forms.SelectMultiple(attrs={"size": 6}),
            "subjects": forms.SelectMultiple(attrs={"size": 6}),
        }


class SupplyForm(forms.ModelForm):
    class Meta:
        model = Supply
        fields = [
            "name",
            "detailed_spec",
            "academic_area",
            "storage_location",
            "total_existing",
            "observations",
        ]
        widgets = {
            "detailed_spec": forms.Textarea(attrs={"rows": 3}),
            "observations": forms.Textarea(attrs={"rows": 3}),
        }


class RequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ["equipment", "supply", "quantity", "reason"]
        widgets = {
            "reason": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        profile = getattr(user, "profile", None)
        area = getattr(profile, "academic_area", None)

        if area:
            self.fields["equipment"].queryset = Equipment.objects.filter(academic_area=area)
            self.fields["supply"].queryset = Supply.objects.filter(academic_area=area)
        else:
            self.fields["equipment"].queryset = Equipment.objects.none()
            self.fields["supply"].queryset = Supply.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        equipment = cleaned_data.get("equipment")
        supply = cleaned_data.get("supply")

        if bool(equipment) == bool(supply):
            raise forms.ValidationError("Selecciona un equipo o un insumo.")

        return cleaned_data


class ImportExcelForm(forms.Form):
    file = forms.FileField(label="Archivo Excel")