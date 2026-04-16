from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0004_requestitem_unique_resources"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="request",
            name="class_datetime",
        ),
        migrations.RemoveField(
            model_name="request",
            name="delivery_datetime",
        ),
        migrations.RemoveField(
            model_name="request",
            name="delivery_delivered_by",
        ),
        migrations.RemoveField(
            model_name="request",
            name="delivery_received_by",
        ),
        migrations.RemoveField(
            model_name="request",
            name="delivery_rut",
        ),
        migrations.RemoveField(
            model_name="request",
            name="observations",
        ),
        migrations.RemoveField(
            model_name="request",
            name="reception_datetime",
        ),
        migrations.RemoveField(
            model_name="request",
            name="reception_delivered_by",
        ),
        migrations.RemoveField(
            model_name="request",
            name="reception_received_by",
        ),
        migrations.RemoveField(
            model_name="request",
            name="student_name",
        ),
        migrations.RemoveField(
            model_name="request",
            name="subject_name",
        ),
        migrations.RemoveField(
            model_name="request",
            name="teacher_name",
        ),
        migrations.RemoveField(
            model_name="request",
            name="work_groups",
        ),
        migrations.RemoveField(
            model_name="requestitem",
            name="delivered",
        ),
        migrations.RemoveField(
            model_name="requestitem",
            name="received",
        ),
    ]
