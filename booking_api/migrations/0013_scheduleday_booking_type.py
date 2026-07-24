from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("booking_api", "0012_alter_booking_booking_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="scheduleday",
            name="booking_type",
            field=models.CharField(
                choices=[("syndicate", "Syndicate"), ("summative", "Summative"), ("group", "Group")],
                default="syndicate",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="scheduleday",
            name="date",
            field=models.DateField(),
        ),
        migrations.AddConstraint(
            model_name="scheduleday",
            constraint=models.UniqueConstraint(
                fields=("date", "booking_type"),
                name="unique_schedule_day_per_type",
            ),
        ),
    ]
