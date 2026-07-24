from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("booking_api", "0010_alter_panel_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="booking_type",
            field=models.CharField(
                choices=[("syndicate", "Syndicate"), ("summative", "Summative")],
                default="syndicate",
                max_length=20,
            ),
        ),
        migrations.RemoveConstraint(
            model_name="booking",
            name="unique_slot_booking",
        ),
        migrations.AddConstraint(
            model_name="booking",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "active")),
                fields=("day", "panel", "role", "slot", "booking_type"),
                name="unique_slot_booking",
            ),
        ),
        migrations.AddConstraint(
            model_name="booking",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "active")),
                fields=("email", "role", "booking_type"),
                name="unique_active_booking_per_email_role_type",
            ),
        ),
    ]
