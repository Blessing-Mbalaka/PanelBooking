"""Count/query helpers for booking metrics."""

from django.db.models.functions import Lower

from booking_api.models import Booking, Panel, ScheduleDay, Slot
from booking_api.models import SupervisorStudentLink


def count_bookings_for_slot(date_value, panel_name, role, slot_label):
    return Booking.objects.filter(
        day__date=date_value, panel__name=panel_name, role=role,
        slot__label=slot_label, status=Booking.STATUS_ACTIVE,
    ).count()


def count_bookings_for_role(date_value, panel_name, role):
    return Booking.objects.filter(
        day__date=date_value, panel__name=panel_name,
        role=role, status=Booking.STATUS_ACTIVE,
    ).count()


def serialize_booking(booking):
    return {
        "id": booking.id,
        "firstName": booking.first_name,
        "surname": booking.surname,
        "name": booking.full_name,
        "email": booking.email,
        "role": booking.role,
        "date": booking.day.date.isoformat(),
        "dateDisplay": booking.day.date.strftime("%A %d %b"),
        "panel": booking.panel.name,
        "slot": booking.slot.label,
        "status": booking.status,
        "cancellationReason": booking.cancellation_reason,
        "cancelledAt": booking.cancelled_at.isoformat() if booking.cancelled_at else None,
        "bookedAt": booking.booked_at.isoformat(),
    }


def get_system_counts():
    student_names = set(
        SupervisorStudentLink.objects
        .annotate(name_key=Lower("student_name"))
        .values_list("name_key", flat=True)
    )
    student_names.update(
        Booking.objects.filter(role=Slot.ROLE_STUDENT)
        .annotate(name_key=Lower("first_name"))
        .values_list("name_key", flat=True)
    )
    supervisor_names = set(
        SupervisorStudentLink.objects
        .annotate(name_key=Lower("supervisor_name"))
        .values_list("name_key", flat=True)
    )
    supervisor_names.update(
        Booking.objects.filter(role=Slot.ROLE_SUPERVISOR)
        .annotate(name_key=Lower("first_name"))
        .values_list("name_key", flat=True)
    )
    return {"students": len(student_names), "supervisors": len(supervisor_names)}
