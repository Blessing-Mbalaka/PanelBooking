from datetime import date, datetime, time, timedelta

from booking_api.models import Panel, ScheduleDay, Slot

DEFAULT_PANELS = ["Panel 1", "Panel 2", "Panel 3", "Panel 4"]
DEFAULT_STUDENT_SLOTS = [
    "10:00 - 10:30",
    "10:30 - 11:00",
    "11:00 - 11:30",
    "11:30 - 12:00",
    "12:30 - 13:00",
]


def build_half_hour_slots(start_at: time = time(9, 0), end_at: time = time(18, 0)) -> list[str]:
    slots = []
    current = datetime.combine(date.today(), start_at)
    boundary = datetime.combine(date.today(), end_at)

    while current < boundary:
        next_time = current + timedelta(minutes=30)
        slots.append(f"{current:%H:%M} - {next_time:%H:%M}")
        current = next_time

    return slots


DEFAULT_BULK_STUDENT_SLOTS = build_half_hour_slots()


def _normalize_values(values: list[str] | None, fallback: list[str]) -> list[str]:
    normalized = []
    seen = set()

    for raw_value in values or fallback:
        value = str(raw_value or "").strip()
        key = value.lower()
        if not value or key in seen:
            continue
        seen.add(key)
        normalized.append(value)

    return normalized


def sync_schedule_day_config(day: ScheduleDay, panels: list[str] | None = None, student_slots: list[str] | None = None) -> ScheduleDay:
    desired_panels = _normalize_values(panels, DEFAULT_PANELS)
    desired_slots = _normalize_values(student_slots, DEFAULT_STUDENT_SLOTS)

    existing_panels = {panel.name: panel for panel in day.panels.all()}
    for panel_name, panel in existing_panels.items():
        if panel_name not in desired_panels:
            panel.delete()

    for index, panel_name in enumerate(desired_panels):
        panel = existing_panels.get(panel_name)
        if panel is None:
            Panel.objects.create(day=day, name=panel_name, sort_order=index)
            continue

        if panel.sort_order != index:
            panel.sort_order = index
            panel.save(update_fields=["sort_order"])

    existing_slots = {
        slot.label: slot
        for slot in day.slots.filter(role=Slot.ROLE_STUDENT)
    }
    for slot_label, slot in existing_slots.items():
        if slot_label not in desired_slots:
            slot.delete()

    for index, slot_label in enumerate(desired_slots):
        slot = existing_slots.get(slot_label)
        if slot is None:
            Slot.objects.create(
                day=day,
                role=Slot.ROLE_STUDENT,
                label=slot_label,
                sort_order=index,
            )
            continue

        if slot.sort_order != index:
            slot.sort_order = index
            slot.save(update_fields=["sort_order"])

    return day


def create_schedule_day_config(
    day_date: date,
    booking_type: str = ScheduleDay.BOOKING_TYPE_SYNDICATE,
    panels: list[str] | None = None,
    student_slots: list[str] | None = None,
) -> ScheduleDay:
    day, _ = ScheduleDay.objects.get_or_create(date=day_date, booking_type=booking_type)
    return sync_schedule_day_config(day, panels=panels, student_slots=student_slots)


def ensure_default_data() -> None:
    return None

