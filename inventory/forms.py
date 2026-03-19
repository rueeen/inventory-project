from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.forms import inlineformset_factory

from .models import Equipment, Supply, Request, RequestItem


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
        fields = [
            "teacher_name",
            "student_name",
            "subject_name",
            "class_datetime",
            "work_groups",
            "reason",
            "delivery_received_by",
            "delivery_rut",
            "delivery_delivered_by",
            "delivery_datetime",
            "reception_delivered_by",
            "reception_received_by",
            "reception_datetime",
            "observations",
        ]
        widgets = {
            "class_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "delivery_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "reception_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "reason": forms.Textarea(attrs={"rows": 2}),
            "observations": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.user = user
        profile = getattr(user, "profile", None)
        area = getattr(profile, "academic_area", None)
        if not self.instance.pk:
            self.fields["student_name"].initial = user.get_full_name() or user.username
        self.area = area


class RequestItemForm(forms.ModelForm):
    class Meta:
        model = RequestItem
        fields = ["equipment", "supply", "quantity", "received", "delivered"]

    def __init__(self, *args, **kwargs):
        area = kwargs.pop("area", None)
        super().__init__(*args, **kwargs)
        equipment_qs = Equipment.objects.filter(academic_area=area) if area else Equipment.objects.none()
        supply_qs = Supply.objects.filter(academic_area=area) if area else Supply.objects.none()
        self.fields["equipment"].queryset = equipment_qs
        self.fields["supply"].queryset = supply_qs
        self.fields["quantity"].widget.attrs.setdefault("min", 1)

    def clean(self):
        cleaned_data = super().clean()
        equipment = cleaned_data.get("equipment")
        supply = cleaned_data.get("supply")
        marked_for_delete = cleaned_data.get("DELETE")

        if marked_for_delete:
            return cleaned_data

        if bool(equipment) == bool(supply):
            raise forms.ValidationError("Selecciona un equipo o un insumo por fila.")

        return cleaned_data


BaseRequestItemFormSet = inlineformset_factory(
    Request,
    RequestItem,
    form=RequestItemForm,
    extra=8,
    can_delete=True,
)


class RequestItemFormSet(BaseRequestItemFormSet):
    def __init__(self, *args, **kwargs):
        self.area = kwargs.pop("area", None)
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs["area"] = self.area
        return super()._construct_form(i, **kwargs)

    def clean(self):
        super().clean()
        valid_forms = [
            form for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        ]
        if not valid_forms:
            raise forms.ValidationError("Debes agregar al menos un insumo o equipo a la solicitud.")


class ImportExcelForm(forms.Form):
    file = forms.FileField(label="Archivo Excel")
