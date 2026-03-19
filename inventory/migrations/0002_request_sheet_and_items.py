from django.db import migrations, models
import django.db.models.deletion


def migrate_request_resources(apps, schema_editor):
    Request = apps.get_model('inventory', 'Request')
    RequestItem = apps.get_model('inventory', 'RequestItem')
    for request in Request.objects.all():
        equipment_id = getattr(request, 'equipment_id', None)
        supply_id = getattr(request, 'supply_id', None)
        quantity = getattr(request, 'quantity', 1) or 1
        if equipment_id or supply_id:
            RequestItem.objects.create(
                request_id=request.id,
                equipment_id=equipment_id,
                supply_id=supply_id,
                quantity=quantity,
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='request',
            name='class_datetime',
            field=models.DateTimeField(default='2026-03-19T00:00:00Z', verbose_name='Fecha y hora de realización de la clase'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='request',
            name='delivery_datetime',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Entrega - Fecha y hora'),
        ),
        migrations.AddField(
            model_name='request',
            name='delivery_delivered_by',
            field=models.CharField(blank=True, max_length=150, verbose_name='Entrega - Entregado por'),
        ),
        migrations.AddField(
            model_name='request',
            name='delivery_received_by',
            field=models.CharField(blank=True, max_length=150, verbose_name='Entrega - Recibido por'),
        ),
        migrations.AddField(
            model_name='request',
            name='delivery_rut',
            field=models.CharField(blank=True, max_length=20, verbose_name='Entrega - RUT'),
        ),
        migrations.AddField(
            model_name='request',
            name='observations',
            field=models.TextField(blank=True, verbose_name='Observaciones'),
        ),
        migrations.AddField(
            model_name='request',
            name='reception_datetime',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Recepción - Fecha y hora'),
        ),
        migrations.AddField(
            model_name='request',
            name='reception_delivered_by',
            field=models.CharField(blank=True, max_length=150, verbose_name='Recepción - Entregado por'),
        ),
        migrations.AddField(
            model_name='request',
            name='reception_received_by',
            field=models.CharField(blank=True, max_length=150, verbose_name='Recepción - Recibido por'),
        ),
        migrations.AddField(
            model_name='request',
            name='student_name',
            field=models.CharField(default='', max_length=150, verbose_name='Alumno'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='request',
            name='subject_name',
            field=models.CharField(default='', max_length=150, verbose_name='Asignatura'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='request',
            name='teacher_name',
            field=models.CharField(blank=True, max_length=150, verbose_name='Docente'),
        ),
        migrations.AddField(
            model_name='request',
            name='work_groups',
            field=models.PositiveIntegerField(default=1, verbose_name='N° de grupos de trabajo'),
        ),
        migrations.CreateModel(
            name='RequestItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='Cantidad solicitada')),
                ('received', models.BooleanField(default=False, verbose_name='Recibido')),
                ('delivered', models.BooleanField(default=False, verbose_name='Entrega')),
                ('equipment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='request_items', to='inventory.equipment')),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='inventory.request')),
                ('supply', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='request_items', to='inventory.supply')),
            ],
            options={
                'verbose_name': 'Ítem de solicitud',
                'verbose_name_plural': 'Ítems de solicitud',
            },
        ),
        migrations.RunPython(migrate_request_resources, noop_reverse),
        migrations.RemoveField(model_name='request', name='equipment'),
        migrations.RemoveField(model_name='request', name='quantity'),
        migrations.RemoveField(model_name='request', name='supply'),
    ]
