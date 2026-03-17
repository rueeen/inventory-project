import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AcademicArea',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True, verbose_name='Área académica')),
            ],
            options={
                'verbose_name': 'Área académica',
                'verbose_name_plural': 'Áreas académicas',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='equipment',
            name='academic_area',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='equipments', to='inventory.academicarea', verbose_name='Área académica'),
        ),
        migrations.AddField(
            model_name='supply',
            name='academic_area',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='supplies', to='inventory.academicarea', verbose_name='Área académica'),
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('student', 'Estudiante'), ('coordinator', 'Coordinador'), ('panol', 'Pañol')], default='student', max_length=20, verbose_name='Rol')),
                ('academic_area', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='users', to='inventory.academicarea', verbose_name='Área académica')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Perfil de usuario',
                'verbose_name_plural': 'Perfiles de usuario',
            },
        ),
        migrations.CreateModel(
            name='Request',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='Cantidad solicitada')),
                ('reason', models.TextField(blank=True, verbose_name='Motivo')),
                ('status', models.CharField(choices=[('pending', 'Pendiente'), ('approved', 'Aprobada'), ('rejected', 'Rechazada')], default='pending', max_length=20)),
                ('academic_area', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='requests', to='inventory.academicarea')),
                ('equipment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='requests', to='inventory.equipment')),
                ('requester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='requests', to=settings.AUTH_USER_MODEL)),
                ('supply', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='requests', to='inventory.supply')),
            ],
            options={
                'verbose_name': 'Solicitud',
                'verbose_name_plural': 'Solicitudes',
                'ordering': ['-created_at'],
            },
        ),
    ]
