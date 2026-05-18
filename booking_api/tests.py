from datetime import date

from django.test import TestCase

from Services.Bookinglogic import create_booking
from booking_api.bootstrap import DEFAULT_SCHEDULE, ensure_default_data
from booking_api.models import Booking, Panel, ScheduleDay, Slot


class DefaultScheduleTests(TestCase):
	def test_ensure_default_data_repairs_missing_supervisor_slots(self):
		ScheduleDay.objects.create(date=DEFAULT_SCHEDULE[0]["date"])

		ensure_default_data()

		for day_config in DEFAULT_SCHEDULE:
			day = ScheduleDay.objects.get(date=day_config["date"])
			self.assertEqual(day.panels.count(), len(day_config["panels"]))
			self.assertEqual(
				Slot.objects.filter(day=day, role=Slot.ROLE_STUDENT).count(),
				len(day_config["student_slots"]),
			)
			self.assertEqual(
				Slot.objects.filter(day=day, role=Slot.ROLE_SUPERVISOR).count(),
				len(day_config["supervisor_slots"]),
			)


class SupervisorBookingTests(TestCase):
	def setUp(self):
		self.day = ScheduleDay.objects.create(date=date(2026, 5, 25))
		self.panel_one = Panel.objects.create(day=self.day, name="Panel 1")
		self.panel_two = Panel.objects.create(day=self.day, name="Panel 2")
		Slot.objects.create(day=self.day, role=Slot.ROLE_SUPERVISOR, label="Supervisor 1")
		Slot.objects.create(day=self.day, role=Slot.ROLE_SUPERVISOR, label="Supervisor 2")

	def test_supervisor_can_have_more_than_one_active_booking(self):
		base_payload = {
			"firstName": "Ada",
			"surname": "Lovelace",
			"email": "ada@example.com",
			"role": Slot.ROLE_SUPERVISOR,
			"supervisor": "Ada Lovelace",
			"date": self.day.date.isoformat(),
			"slot": "Supervisor 1",
		}

		create_booking({**base_payload, "panel": self.panel_one.name})
		create_booking({**base_payload, "panel": self.panel_two.name})

		self.assertEqual(
			Booking.objects.filter(
				email__iexact="ada@example.com",
				role=Slot.ROLE_SUPERVISOR,
				status=Booking.STATUS_ACTIVE,
			).count(),
			2,
		)
