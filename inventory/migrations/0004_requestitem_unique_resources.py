from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0003_alter_career_options_alter_storagelocation_options_and_more"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="requestitem",
            constraint=models.UniqueConstraint(
                condition=models.Q(equipment__isnull=False),
                fields=("request", "equipment"),
                name="requestitem_unique_equipment_per_request",
            ),
        ),
        migrations.AddConstraint(
            model_name="requestitem",
            constraint=models.UniqueConstraint(
                condition=models.Q(supply__isnull=False),
                fields=("request", "supply"),
                name="requestitem_unique_supply_per_request",
            ),
        ),
    ]
