from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from .forms import RequestForm
from .models import AcademicArea, Equipment, Request, StorageLocation, Supply


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
