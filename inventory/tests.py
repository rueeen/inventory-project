from io import BytesIO

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook

from .forms import RequestForm
from .models import AcademicArea, Equipment, EquipmentCode, Request, StorageLocation, Supply
from .services.importers import import_equipment_excel


class RequestModelTests(TestCase):
    def setUp(self):
        self.area = AcademicArea.objects.create(name="Informática")
        self.other_area = AcademicArea.objects.create(name="Electrónica")
        self.storage = StorageLocation.objects.create(name="Bodega")
        self.equipment = Equipment.objects.create(
            name="Osciloscopio",
            storage_location=self.storage,
            academic_area=self.area,
            total_existing=1,
            good_count=1,
            repairable_count=0,
            bad_count=0,
        )

    def test_request_requires_single_resource(self):
        user = User.objects.create_user(username="ana", password="123")
        request = Request(
            requester=user,
            academic_area=self.area,
            quantity=1,
        )
        with self.assertRaises(ValidationError):
            request.full_clean()

    def test_request_validates_area(self):
        user = User.objects.create_user(username="juan", password="123")
        request = Request(
            requester=user,
            academic_area=self.other_area,
            equipment=self.equipment,
            quantity=1,
        )
        with self.assertRaises(ValidationError):
            request.full_clean()


class RequestFormTests(TestCase):
    def setUp(self):
        self.area = AcademicArea.objects.create(name="Informática")
        self.other_area = AcademicArea.objects.create(name="Electrónica")
        self.storage = StorageLocation.objects.create(name="Pañol")
        self.equipment = Equipment.objects.create(
            name="Taladro",
            storage_location=self.storage,
            academic_area=self.area,
            total_existing=1,
            good_count=1,
            repairable_count=0,
            bad_count=0,
        )
        self.foreign_supply = Supply.objects.create(
            name="Cables",
            storage_location=self.storage,
            academic_area=self.other_area,
            total_existing=20,
        )

    def test_form_filters_items_by_user_area(self):
        user = User.objects.create_user(username="est", password="123")
        user.profile.academic_area = self.area
        user.profile.save()

        form = RequestForm(user=user)
        self.assertIn(self.equipment, form.fields["equipment"].queryset)
        self.assertNotIn(self.foreign_supply, form.fields["supply"].queryset)


class ImportEquipmentExcelTests(TestCase):
    def _build_workbook(self):
        wb = Workbook()
        ws = wb.active
        ws.append([
            "Código Inventario",
            "Equipo",
            "Especificación Técnica Detallada",
            "Carrera(s) que Utiliza el Equipo",
            "Código(s)-Nombre(s) de Asignatura(s)",
            "Lugar de Almacenamiento",
            "Cantidad Total Existente en la Sede",
            "Cantidad Necesaria",
            "Brecha Existente",
            "Bueno",
            "Reparable",
            "Malo",
            "UF (c/iva)",
            "Valor Total",
            "Observaciones",
        ])
        ws.append([
            "UTC000437291\n180000003256",
            "Computador all-in-one Hp",
            "Intel core i7-7700T 2.90GHz, 16 GB RAM, Intel HD Graphics 630",
            "Analista programador e Ingenieria en informatica",
            "TI3012,TI3013",
            "LEICA",
            1,
            1,
            0,
            1,
            0,
            0,
            "",
            "",
            "",
        ])
        ws.append([
            "UTC000437114\n180000007008",
            "Computador all-in-one Hp",
            "Intel core i7-7700T 2.90GHz, 16 GB RAM, Intel HD Graphics 631",
            "Analista programador e Ingenieria en informatica",
            "TI3012,TI3013",
            "LEICA",
            1,
            1,
            0,
            1,
            0,
            0,
            "",
            "",
            "",
        ])

        stream = BytesIO()
        wb.save(stream)
        stream.seek(0)
        return stream

    def test_import_creates_one_equipment_per_excel_row_when_codes_are_distinct(self):
        result = import_equipment_excel(self._build_workbook())

        self.assertEqual(result["errors"], [])
        self.assertEqual(result["created"], 2)
        self.assertEqual(Equipment.objects.count(), 2)
        self.assertEqual(EquipmentCode.objects.count(), 4)


class LogoutViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="logout-user", password="12345678")
        self.logout_url = reverse("inventory:logout")
        self.home_url = reverse("inventory:equipment_list")

    def test_logout_post_ends_session_and_redirects_to_login(self):
        self.client.force_login(self.user)

        response = self.client.post(self.logout_url, follow=True)

        self.assertRedirects(response, reverse("inventory:login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_get_also_ends_session_and_redirects_to_login(self):
        self.client.force_login(self.user)

        response = self.client.get(self.logout_url, follow=True)

        self.assertRedirects(response, reverse("inventory:login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.logout_url)

        self.assertRedirects(response, f"{reverse('inventory:login')}?next={self.logout_url}")
