"""Count/query helpers for booking metrics."""

from django.db.models import Value
from django.db.models.functions import Concat
from django.db.models.functions import Lower

from booking_api.models import Booking, Panel, ScheduleDay, Slot
from booking_api.models import SupervisorStudentLink


def count_bookings_for_slot(date_value: str, panel_name: str, role: str, slot_label: str) -> int:
	return Booking.objects.filter(
		day__date=date_value,
		panel__name=panel_name,
		role=role,
		slot__label=slot_label,
	).count()


def count_bookings_for_role(date_value: str, panel_name: str, role: str) -> int:
	return Booking.objects.filter(
		day__date=date_value,
		panel__name=panel_name,
		role=role,
	).count()


def serialize_booking(booking: Booking) -> dict:
	return {
		"id": booking.id,
		"firstName": booking.first_name,
		"surname": booking.surname,
		"name": booking.full_name,
		"email": booking.email,
		"bookingType": booking.booking_type,
		"role": booking.role,
		"supervisor": booking.supervisor or "",
		"supervisorName": booking.co_supervisor or "",
		"date": booking.day.date.isoformat(),
		"dateDisplay": booking.day.date.strftime("%A %d %b"),
		"panel": booking.panel.name,
		"slot": booking.slot.label,
		"status": booking.status,
		"cancellationReason": booking.cancellation_reason,
		"cancelledAt": booking.cancelled_at.isoformat() if booking.cancelled_at else None,
		"bookedAt": booking.booked_at.isoformat() if booking.booked_at else None,
    }
def get_system_counts() -> dict:
	booking_name_expression = Lower(Concat("first_name", Value(" "), "surname"))

	student_names = set(
		SupervisorStudentLink.objects.annotate(name_key=Lower("student_name")).values_list("name_key", flat=True)
	)
	student_names.update(
		Booking.objects.filter(role=Slot.ROLE_STUDENT)
		.annotate(name_key=booking_name_expression)
		.values_list("name_key", flat=True)
	)

	supervisor_names = set(
		SupervisorStudentLink.objects.annotate(name_key=Lower("supervisor_name")).values_list("name_key", flat=True)
	)
	supervisor_names.update(
		Booking.objects.filter(role=Slot.ROLE_SUPERVISOR)
		.annotate(name_key=booking_name_expression)
		.values_list("name_key", flat=True)
	)

	return {
		"students": len(student_names),
		"supervisors": len(supervisor_names),
	}
    
