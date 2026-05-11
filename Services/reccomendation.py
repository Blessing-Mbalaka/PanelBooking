"""Recommendation and panel-conflict business rules."""

from booking_api.models import Booking, Slot, SupervisorStudentLink


def _has_matching_booking(names: list[str], role: str, date_value, panel) -> bool:
	if not names:
		return False
	# names here are full names from SupervisorStudentLink; match against first_name + surname
	# build a case-insensitive full-name filter using Q objects
	from django.db.models import Q, Value
	from django.db.models.functions import Concat
	qs = Booking.objects.annotate(
		full_name=Concat("first_name", Value(" "), "surname")
	).filter(role=role, day=date_value, panel=panel, status=Booking.STATUS_ACTIVE)
	q = Q()
	for n in names:
		q |= Q(full_name__iexact=n)
	return qs.filter(q).exists()


def violates_supervisor_student_rule(name: str, role: str, day, panel) -> bool:
	"""Supervisors and their students cannot be booked into the same panel/day."""
	if role == Slot.ROLE_STUDENT:
		supervisor_names = list(
			SupervisorStudentLink.objects.filter(student_name__iexact=name)
			.values_list("supervisor_name", flat=True)
		)
		return _has_matching_booking(supervisor_names, Slot.ROLE_SUPERVISOR, day, panel)

	if role == Slot.ROLE_SUPERVISOR:
		student_names = list(
			SupervisorStudentLink.objects.filter(supervisor_name__iexact=name)
			.values_list("student_name", flat=True)
		)
		return _has_matching_booking(student_names, Slot.ROLE_STUDENT, day, panel)

	return False


def recommend_supervisor_slots(supervisor_name: str, slots_queryset, day, panel) -> list[str]:
	"""Return open supervisor slots for a supervisor after applying student conflict rule."""
	if violates_supervisor_student_rule(supervisor_name, Slot.ROLE_SUPERVISOR, day, panel):
		return []

	taken_slot_ids = set(
		Booking.objects.filter(day=day, panel=panel, role=Slot.ROLE_SUPERVISOR)
		.values_list("slot_id", flat=True)
	)

	return [slot.label for slot in slots_queryset if slot.id not in taken_slot_ids]
