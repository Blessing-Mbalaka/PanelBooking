"""Input validation utilities for booking payloads."""

import re


class BookingValidationError(ValueError):
	"""Raised when booking payload validation fails."""


def normalize_name(name: str) -> str:
	return " ".join((name or "").strip().split())


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_booking_payload(payload: dict) -> dict:
	if not isinstance(payload, dict):
		raise BookingValidationError("Invalid payload.")

	first_name = normalize_name(payload.get("firstName", "") or payload.get("first_name", ""))
	surname = normalize_name(payload.get("surname", ""))
	email = (payload.get("email", "") or "").strip().lower()
	role = (payload.get("role", "") or "").strip().lower()
	supervisor = (payload.get("supervisor", "") or "").strip()
	co_supervisor_name = (payload.get("coSupervisorName", "") or payload.get("co_supervisor_name", "")).strip()
	date_value = (payload.get("date", "") or "").strip()
	panel = (payload.get("panel", "") or "").strip()
	slot = (payload.get("slot", "") or "").strip()

	if not first_name:
		raise BookingValidationError("Enter first name.")

	if not surname:
		raise BookingValidationError("Enter surname.")

	if not email or not _EMAIL_RE.match(email):
		raise BookingValidationError("Enter a valid email address.")

	if role not in {"student", "supervisor"}:
		raise BookingValidationError("Select a valid role.")

	if not date_value:
		raise BookingValidationError("Select a date.")

	if not panel:
		raise BookingValidationError("Select a panel.")

	if not slot:
		raise BookingValidationError("Choose open slot.")

	return {
		"first_name": first_name,
		"surname": surname,
		"email": email,
		"role": role,
		"supervisor": supervisor,
		"co_supervisor": co_supervisor_name,
		"date": date_value,
		"panel": panel,
		"slot": slot,
	}