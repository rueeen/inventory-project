from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Equipment, Request, Supply


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
        fields = ["reason"]
        widgets = {
            "reason": forms.Textarea(attrs={"rows": 4, "placeholder": "Explica el motivo general de esta solicitud"}),
        }


class CartQuantityForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, label="Cantidad")


class ImportExcelForm(forms.Form):
    file = forms.FileField(label="Archivo Excel")
