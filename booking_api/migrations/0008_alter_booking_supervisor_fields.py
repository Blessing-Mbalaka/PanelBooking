from django.db import migrations, models


class Migration(migrations.Migration):
	dependencies = [
		("booking_api", "0007_rename_supervisor_name_booking_co_supervisor"),
	]

	operations = [
		migrations.AlterField(
			model_name="booking",
			name="supervisor",
			field=models.CharField(blank=True, default="", max_length=255, null=True),
		),
		migrations.AlterField(
			model_name="booking",
			name="co_supervisor",
			field=models.CharField(blank=True, default="", max_length=255, null=True),
		),
	]