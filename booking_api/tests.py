from datetime import date

from django.test import TestCase
from django.urls import reverse

from Services.Bookinglogic import create_booking
from booking_api.bootstrap import DEFAULT_PANELS, DEFAULT_STUDENT_SLOTS, create_schedule_day_config
from booking_api.models import Booking, Panel, ScheduleDay, Slot


class ScheduleConfigurationTests(TestCase):
	def test_create_schedule_day_config_applies_default_structure(self):
		day = create_schedule_day_config(date(2026, 5, 25))

		self.assertEqual(day.panels.count(), len(DEFAULT_PANELS))
		self.assertEqual(
			Slot.objects.filter(day=day, role=Slot.ROLE_STUDENT).count(),
			len(DEFAULT_STUDENT_SLOTS),
		)

	def test_schedule_date_endpoint_requires_password_and_creates_date(self):
		response = self.client.post(
			reverse("schedule-days"),
			data='{"password":"uj-booking-settings","date":"2026-05-25","panels":["Panel 1","Panel 2","Panel 5"],"studentSlots":["09:00 - 09:20","09:20 - 09:40"]}',
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 201)
		day = ScheduleDay.objects.get(date="2026-05-25")
		self.assertEqual(list(day.panels.values_list("name", flat=True)), ["Panel 1", "Panel 2", "Panel 5"])
		self.assertEqual(list(day.panels.values_list("sort_order", flat=True)), [0, 1, 2])
		self.assertEqual(
			list(day.slots.filter(role=Slot.ROLE_STUDENT).order_by("sort_order").values_list("label", flat=True)),
			["09:00 - 09:20", "09:20 - 09:40"],
		)

	def test_schedule_date_endpoint_updates_existing_date_configuration(self):
		day = create_schedule_day_config(date(2026, 5, 25))
		response = self.client.post(
			reverse("schedule-days"),
			data='{"password":"uj-booking-settings","date":"2026-05-25","panels":["Panel A"],"studentSlots":["15:00 - 15:30"]}',
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 201)
		day.refresh_from_db()
		self.assertEqual(list(day.panels.values_list("name", flat=True)), ["Panel A"])
		self.assertEqual(
			list(day.slots.filter(role=Slot.ROLE_STUDENT).values_list("label", flat=True)),
			["15:00 - 15:30"],
		)

	def test_schedule_date_endpoint_preserves_panel_order(self):
		response = self.client.post(
			reverse("schedule-days"),
			data='{"password":"uj-booking-settings","date":"2026-05-26","panels":["Zulu","Alpha","Bravo"],"studentSlots":["09:00 - 09:20"]}',
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 201)
		day = ScheduleDay.objects.get(date="2026-05-26")
		self.assertEqual(list(day.panels.values_list("name", flat=True)), ["Zulu", "Alpha", "Bravo"])

	def test_schedule_date_delete_rejects_dates_with_bookings(self):
		day = create_schedule_day_config(date(2026, 5, 25))
		panel = Panel.objects.get(day=day, name="Panel 1")
		slot = Slot.objects.get(day=day, role=Slot.ROLE_STUDENT, label=DEFAULT_STUDENT_SLOTS[0])
		Booking.objects.create(
			first_name="Ada",
			surname="Lovelace",
			email="ada@example.com",
			role=Slot.ROLE_STUDENT,
			day=day,
			panel=panel,
			slot=slot,
		)

		response = self.client.delete(
			reverse("schedule-days"),
			data='{"password":"uj-booking-settings","date":"2026-05-25"}',
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 400)

	def test_schedule_date_update_rejects_removing_booked_slot(self):
		day = create_schedule_day_config(date(2026, 5, 25))
		panel = Panel.objects.get(day=day, name="Panel 1")
		slot = Slot.objects.get(day=day, role=Slot.ROLE_STUDENT, label=DEFAULT_STUDENT_SLOTS[0])
		Booking.objects.create(
			first_name="Ada",
			surname="Lovelace",
			email="ada@example.com",
			role=Slot.ROLE_STUDENT,
			day=day,
			panel=panel,
			slot=slot,
		)

		response = self.client.post(
			reverse("schedule-days"),
			data='{"password":"uj-booking-settings","date":"2026-05-25","panels":["Panel 1"],"studentSlots":["11:00 - 11:30"]}',
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 400)



class StudentBookingTests(TestCase):
	def setUp(self):
		self.day = ScheduleDay.objects.create(date=date(2026, 5, 25))
		self.panel_one = Panel.objects.create(day=self.day, name="Panel 1")
		Slot.objects.create(day=self.day, role=Slot.ROLE_STUDENT, label="10:00 - 10:30")

	def test_student_booking_allows_blank_supervisor(self):
		booking = create_booking({
			"firstName": "Ada",
			"surname": "Lovelace",
			"email": "ada@example.com",
			"role": Slot.ROLE_STUDENT,
			"supervisor": "",
			"date": self.day.date.isoformat(),
			"slot": "10:00 - 10:30",
			"panel": self.panel_one.name,
		})

		self.assertEqual(booking["role"], Slot.ROLE_STUDENT)
		self.assertEqual(booking["supervisor"], "")


class CancelBookingTests(TestCase):
	def setUp(self):
		self.day = create_schedule_day_config(date(2026, 5, 25), panels=["Panel 1"], student_slots=["10:00 - 10:30"])
		self.panel = Panel.objects.get(day=self.day, name="Panel 1")
		self.slot = Slot.objects.get(day=self.day, role=Slot.ROLE_STUDENT, label="10:00 - 10:30")
		self.booking = Booking.objects.create(
			first_name="Ada",
			surname="Lovelace",
			email="ada@example.com",
			role=Slot.ROLE_STUDENT,
			day=self.day,
			panel=self.panel,
			slot=self.slot,
		)

	def test_settings_can_cancel_active_booking(self):
		response = self.client.post(
			reverse("admin-cancel-booking", args=[self.booking.id]),
			data='{"password":"uj-booking-settings","reason":"Cancelled by admin."}',
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 200)
		self.booking.refresh_from_db()
		self.assertEqual(self.booking.status, Booking.STATUS_CANCELLED)
		self.assertEqual(self.booking.cancellation_reason, "Cancelled by admin.")
