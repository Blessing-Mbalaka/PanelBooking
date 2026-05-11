from datetime import date

from booking_api.models import Panel, ScheduleDay, Slot

DEFAULT_SCHEDULE = [
    {
        "date": date(2026, 5, 25),
        "panels": ["Panel 1", "Panel 2", "Panel 3", "Panel 4"],
        "student_slots": ["10:00 - 10:30", "10:30 - 11:00", "11:00 - 11:30", "11:30 - 12:00", "12:30 - 13:00"],
        "supervisor_slots": ["Supervisor 1", "Supervisor 2"],
    },
    {
        "date": date(2026, 5, 26),
        "panels": ["Panel 1", "Panel 2", "Panel 3", "Panel 4"],
        "student_slots": ["10:00 - 10:30", "10:30 - 11:00", "11:00 - 11:30", "11:30 - 12:00", "12:30 - 13:00"],
        "supervisor_slots": ["Supervisor 1", "Supervisor 2"],
    },
    {
        "date": date(2026, 5, 27),
        "panels": ["Panel 1", "Panel 2", "Panel 3", "Panel 4"],
        "student_slots": ["10:00 - 10:30", "10:30 - 11:00", "11:00 - 11:30", "11:30 - 12:00", "12:30 - 13:00"],
        "supervisor_slots": ["Supervisor 1", "Supervisor 2"],
    },
    {
        "date": date(2026, 5, 28),
        "panels": ["Panel 1", "Panel 2"],
        "student_slots": ["10:00 - 10:30", "10:30 - 11:00", "11:00 - 11:30", "11:30 - 12:00", "12:30 - 13:00"],
        "supervisor_slots": ["Supervisor 1", "Supervisor 2"],
    },
]

def ensure_default_data() -> None:
    if ScheduleDay.objects.exists():
        return

    for day_config in DEFAULT_SCHEDULE:
        day, _ = ScheduleDay.objects.get_or_create(date=day_config["date"])

        for panel_name in day_config["panels"]:
            Panel.objects.get_or_create(day=day, name=panel_name)

        for index, slot_label in enumerate(day_config["student_slots"]):
            Slot.objects.get_or_create(
                day=day,
                role=Slot.ROLE_STUDENT,
                label=slot_label,
                defaults={"sort_order": index},
            )

        for index, slot_label in enumerate(day_config["supervisor_slots"]):
            Slot.objects.get_or_create(
                day=day,
                role=Slot.ROLE_SUPERVISOR,
                label=slot_label,
                defaults={"sort_order": index},
            )

