from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AcademicArea(models.Model):
    name = models.CharField("Área académica", max_length=150, unique=True)

    class Meta:
        verbose_name = "Área académica"
        verbose_name_plural = "Áreas académicas"
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    class Roles(models.TextChoices):
        STUDENT = "student", "Estudiante"
        COORDINATOR = "coordinator", "Coordinador"
        PANOL = "panol", "Pañol"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Usuario",
    )
    role = models.CharField(
        "Rol",
        max_length=20,
        choices=Roles.choices,
        default=Roles.STUDENT,
    )
    academic_area = models.ForeignKey(
        AcademicArea,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
        verbose_name="Área académica",
    )

    class Meta:
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuario"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        UserProfile.objects.get_or_create(user=instance)


class StorageLocation(models.Model):
    name = models.CharField("Lugar de almacenamiento",
                            max_length=150, unique=True)

    class Meta:
        verbose_name = "Lugar de almacenamiento"
        verbose_name_plural = "Lugares de almacenamiento"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Career(models.Model):
    name = models.CharField("Carrera", max_length=150, unique=True)

    class Meta:
        verbose_name = "Carrera"
        verbose_name_plural = "Carreras"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Subject(models.Model):
    code = models.CharField("Código", max_length=30, unique=True)
    name = models.CharField("Asignatura", max_length=150, blank=True)

    class Meta:
        verbose_name = "Asignatura"
        verbose_name_plural = "Asignaturas"
        ordering = ["code", "name"]

    def __str__(self):
        return f"{self.code} - {self.name}" if self.name else self.code


class Equipment(TimeStampedModel):
    class Conditions(models.TextChoices):
        GOOD = "good", "Bueno"
        REPAIRABLE = "repairable", "Reparable"
        BAD = "bad", "Malo"

    inventory_code = models.CharField(
        "Código inventario", max_length=100, unique=True)
    name = models.CharField("Equipo", max_length=200)
    detailed_spec = models.TextField(
        "Especificación técnica detallada", blank=True)

    academic_area = models.ForeignKey(
        AcademicArea,
        on_delete=models.PROTECT,
        related_name="equipments",
        verbose_name="Área académica",
    )
    careers = models.ManyToManyField(
        Career, blank=True, verbose_name="Carreras")
    subjects = models.ManyToManyField(
        Subject, blank=True, verbose_name="Asignaturas")

    storage_location = models.ForeignKey(
        StorageLocation,
        on_delete=models.PROTECT,
        related_name="equipments",
        verbose_name="Lugar de almacenamiento",
    )

    condition = models.CharField(
        "Estado",
        max_length=20,
        choices=Conditions.choices,
        default=Conditions.GOOD,
    )

    unit_value_uf = models.DecimalField(
        "Valor unitario UF (c/iva)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    observations = models.TextField("Observaciones", blank=True)

    class Meta:
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"
        ordering = ["name", "inventory_code"]

    def __str__(self):
        return f"{self.inventory_code} - {self.name}"


class Supply(TimeStampedModel):
    name = models.CharField("Insumo", max_length=200)
    detailed_spec = models.TextField(
        "Especificación técnica detallada", blank=True)

    academic_area = models.ForeignKey(
        AcademicArea,
        on_delete=models.PROTECT,
        related_name="supplies",
        verbose_name="Área académica",
    )

    storage_location = models.ForeignKey(
        StorageLocation,
        on_delete=models.PROTECT,
        related_name="supplies",
        verbose_name="Lugar de almacenamiento",
    )

    total_existing = models.PositiveIntegerField(
        "Cantidad total existente en el laboratorio / taller",
        default=0,
    )

    observations = models.TextField("Observaciones", blank=True)

    class Meta:
        verbose_name = "Insumo"
        verbose_name_plural = "Insumos"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Request(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        APPROVED = "approved", "Aprobada"
        REJECTED = "rejected", "Rechazada"

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="requests",
        verbose_name="Solicitante",
    )
    academic_area = models.ForeignKey(
        AcademicArea,
        on_delete=models.PROTECT,
        related_name="requests",
        verbose_name="Área académica",
    )
    teacher_name = models.CharField("Docente", max_length=150, blank=True)
    student_name = models.CharField("Alumno", max_length=150)
    subject_name = models.CharField("Asignatura", max_length=150)
    class_datetime = models.DateTimeField(
        "Fecha y hora de realización de la clase")
    work_groups = models.PositiveIntegerField(
        "N° de grupos de trabajo",
        default=1,
        validators=[MinValueValidator(1)],
    )
    reason = models.TextField("Motivo", blank=True)
    status = models.CharField(
        "Estado",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    delivery_received_by = models.CharField(
        "Entrega - Recibido por", max_length=150, blank=True)
    delivery_rut = models.CharField("Entrega - RUT", max_length=20, blank=True)
    delivery_delivered_by = models.CharField(
        "Entrega - Entregado por", max_length=150, blank=True)
    delivery_datetime = models.DateTimeField(
        "Entrega - Fecha y hora", null=True, blank=True)
    reception_delivered_by = models.CharField(
        "Recepción - Entregado por", max_length=150, blank=True)
    reception_received_by = models.CharField(
        "Recepción - Recibido por", max_length=150, blank=True)
    reception_datetime = models.DateTimeField(
        "Recepción - Fecha y hora", null=True, blank=True)
    observations = models.TextField("Observaciones", blank=True)

    class Meta:
        verbose_name = "Solicitud"
        verbose_name_plural = "Solicitudes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.requester.username} - {self.subject_name}"

    @property
    def total_quantity(self):
        return self.items.aggregate(total=Sum("quantity"))["total"] or 0

    @property
    def status_display(self):
        return self.get_status_display()

    @property
    def items_summary(self):
        return [f"{item.resource_name} x{item.quantity}" for item in self.items.all()]


class RequestItem(models.Model):
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Solicitud",
    )
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,
        related_name="request_items",
        null=True,
        blank=True,
        verbose_name="Equipo",
    )
    supply = models.ForeignKey(
        Supply,
        on_delete=models.PROTECT,
        related_name="request_items",
        null=True,
        blank=True,
        verbose_name="Insumo",
    )
    quantity = models.PositiveIntegerField(
        "Cantidad solicitada",
        default=1,
        validators=[MinValueValidator(1)],
    )
    received = models.BooleanField("Recibido", default=False)
    delivered = models.BooleanField("Entrega", default=False)

    class Meta:
        verbose_name = "Ítem de solicitud"
        verbose_name_plural = "Ítems de solicitud"
        constraints = [
            models.CheckConstraint(
                check=(
                    (
                        models.Q(equipment__isnull=False)
                        & models.Q(supply__isnull=True)
                    )
                    | (
                        models.Q(equipment__isnull=True)
                        & models.Q(supply__isnull=False)
                    )
                ),
                name="requestitem_exactly_one_resource",
            )
        ]

    def __str__(self):
        resource = self.equipment or self.supply
        return f"{self.request} - {resource}"

    @property
    def resource_name(self):
        resource = self.equipment or self.supply
        return str(resource) if resource else ""

    def clean(self):
        super().clean()

        if bool(self.equipment) == bool(self.supply):
            raise ValidationError(
                "Debes seleccionar un equipo o un insumo, pero no ambos."
            )

        item = self.equipment or self.supply
        if item and self.request_id and item.academic_area_id != self.request.academic_area_id:
            raise ValidationError(
                "El recurso solicitado no pertenece al área académica seleccionada."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
