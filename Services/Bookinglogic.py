"""Core booking orchestration logic for API views."""

from django.db import IntegrityError, transaction
from django.utils import timezone

from booking_api.models import Booking, Panel, ScheduleDay, Slot, SupervisorStudentLink
from Services.count import serialize_booking
from Services.form import BookingValidationError, validate_booking_payload
from Services.reccomendation import violates_supervisor_student_rule


class BookingConflictError(ValueError):
	"""Raised when booking rules are violated."""


def list_bookings() -> list[dict]:
	queryset = Booking.objects.select_related("day", "panel", "slot").filter(
		status=Booking.STATUS_ACTIVE
	)
	return [serialize_booking(booking) for booking in queryset]


def clear_bookings() -> int:
	deleted_count, _ = Booking.objects.all().delete()
	return deleted_count


def _identity_is_registered(first_name: str, surname: str, email: str, role: str) -> bool:
	"""
	Return True if the person is registered in SupervisorStudentLink for the correct role.
	Matches on full name AND email (when email is stored). Skips check if table is empty.
	"""
	full_name = f"{first_name} {surname}".strip()
	if not SupervisorStudentLink.objects.exists():
		return True  # no mapping uploaded — allow booking

	if role == Slot.ROLE_STUDENT:
		name_match = SupervisorStudentLink.objects.filter(student_name__iexact=full_name)
		if not name_match.exists():
			return False
		# If any row for this student has an email stored, the submitted email must match
		with_email = name_match.exclude(student_email="")
		if with_email.exists():
			return with_email.filter(student_email__iexact=email).exists()
		return True

	# supervisor
	name_match = SupervisorStudentLink.objects.filter(supervisor_name__iexact=full_name)
	if not name_match.exists():
		return False
	with_email = name_match.exclude(supervisor_email="")
	if with_email.exists():
		return with_email.filter(supervisor_email__iexact=email).exists()
	return True


@transaction.atomic
def create_booking(payload: dict) -> dict:
	data = validate_booking_payload(payload)

	# Identity check — name+surname (and email if stored) must match the registered database
	if not _identity_is_registered(data["first_name"], data["surname"], data["email"], data["role"]):
		raise BookingConflictError(
			"Your name and surname do not match any registered person for that role. "
			"Please contact the administrator if you believe this is an error."
		)

	day = ScheduleDay.objects.filter(date=data["date"]).first()
	if day is None:
		raise BookingValidationError("Select a valid date.")

	panel = Panel.objects.filter(day=day, name=data["panel"]).first()
	if panel is None:
		raise BookingValidationError("Select a valid panel.")

	slot = Slot.objects.filter(day=day, role=data["role"], label=data["slot"]).first()
	if slot is None:
		raise BookingValidationError("Choose a valid slot.")

	# One active booking per email + role (students only)
	if data["role"] == Slot.ROLE_STUDENT:
		if Booking.objects.filter(
			email__iexact=data["email"], role=data["role"], status=Booking.STATUS_ACTIVE
		).exists():
			raise BookingConflictError(
				"You already have an active booking for this role. "
				"Cancel your existing booking before making a new one."
			)

	if Booking.objects.filter(
		day=day, panel=panel, role=data["role"], slot=slot, status=Booking.STATUS_ACTIVE
	).exists():
		raise BookingConflictError("Slot taken.")

	full_name = f"{data['first_name']} {data['surname']}"
	if violates_supervisor_student_rule(full_name, data["role"], day, panel):
		raise BookingConflictError("Supervisors cannot be in the same panel as their student.")

	try:
		booking = Booking.objects.create(
			first_name=data["first_name"],
			surname=data["surname"],
			email=data["email"],
			role=data["role"],
			supervisor=data["supervisor"],
			co_supervisor=data["co_supervisor"],
			day=day,
			panel=panel,
			slot=slot,
		)
	except IntegrityError as error:
		if "unique_slot_booking" in str(error):
			raise BookingConflictError("Slot taken.") from error
		raise
	return serialize_booking(booking)


@transaction.atomic
def cancel_booking(booking_id: int, email: str, reason: str) -> dict:
	"""
	Cancel an active booking. Verifies the email matches so only the
	booking owner can cancel. Returns the updated booking.
	"""
	email = (email or "").strip().lower()
	reason = (reason or "").strip()

	if not reason:
		raise BookingValidationError("Provide a reason for cancellation.")

	try:
		booking = Booking.objects.select_related("day", "panel", "slot").get(
			pk=booking_id, status=Booking.STATUS_ACTIVE
		)
	except Booking.DoesNotExist:
		raise BookingValidationError("Booking not found or already cancelled.")

	if booking.email.lower() != email:
		raise BookingConflictError("Email does not match the booking record.")

	booking.status = Booking.STATUS_CANCELLED
	booking.cancellation_reason = reason
	booking.cancelled_at = timezone.now()
	booking.save(update_fields=["status", "cancellation_reason", "cancelled_at"])
	return serialize_booking(booking)

