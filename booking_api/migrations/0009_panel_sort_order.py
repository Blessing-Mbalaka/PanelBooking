from django.db import migrations, models


class Migration(migrations.Migration):
	dependencies = [
		("booking_api", "0008_alter_booking_supervisor_fields"),
	]

	operations = [
		migrations.AddField(
			model_name="panel",
			name="sort_order",
			field=models.PositiveIntegerField(default=0),
		),
	]