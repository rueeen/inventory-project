from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Equipment, Supply, EquipmentCode, Request


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)


class EquipmentForm(forms.ModelForm):
    codes_text = forms.CharField(
        label="Códigos",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Ingresa un código por línea."
    )

    class Meta:
        model = Equipment
        fields = [
            "name",
            "detailed_spec",
            "academic_area",
            "careers",
            "subjects",
            "storage_location",
            "total_existing",
            "quantity_needed",
            "good_count",
            "repairable_count",
            "bad_count",
            "unit_value_uf",
            "observations",
        ]
        widgets = {
            "detailed_spec": forms.Textarea(attrs={"rows": 3}),
            "observations": forms.Textarea(attrs={"rows": 3}),
            "careers": forms.SelectMultiple(attrs={"size": 6}),
            "subjects": forms.SelectMultiple(attrs={"size": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["codes_text"].initial = "\n".join(
                self.instance.codes.values_list("code", flat=True)
            )

    def clean(self):
        cleaned_data = super().clean()
        total_existing = cleaned_data.get("total_existing", 0)
        good_count = cleaned_data.get("good_count", 0)
        repairable_count = cleaned_data.get("repairable_count", 0)
        bad_count = cleaned_data.get("bad_count", 0)

        if (good_count + repairable_count + bad_count) != total_existing:
            raise forms.ValidationError(
                "La suma de Bueno + Reparable + Malo debe coincidir con la cantidad total existente."
            )
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=commit)

        if commit:
            codes = self.cleaned_data.get("codes_text", "")
            code_list = [c.strip() for c in codes.splitlines() if c.strip()]

            instance.codes.exclude(code__in=code_list).delete()

            existing_codes = set(instance.codes.values_list("code", flat=True))
            for code in code_list:
                if code not in existing_codes:
                    EquipmentCode.objects.create(equipment=instance, code=code)

        return instance


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
