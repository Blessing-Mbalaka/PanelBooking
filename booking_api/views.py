import json
import csv
from io import TextIOWrapper
from pathlib import Path

from openpyxl import load_workbook

from django.http import JsonResponse, FileResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from Services.Bookinglogic import BookingConflictError, cancel_booking, clear_bookings, create_booking, list_bookings
from Services.count import get_system_counts
from Services.form import BookingValidationError
from Services.reccomendation import recommend_supervisor_slots
from booking_api.bootstrap import ensure_default_data
from booking_api.models import Panel, ScheduleDay, Slot, SupervisorStudentLink, Supervisor


@ensure_csrf_cookie
def index(request):
	return render(request, "booking_api/index.html")


@ensure_csrf_cookie
def load_data_page(request):
	return render(request, "booking_api/load_data.html")


@require_http_methods(["GET"])
def schedule_config(request):
	ensure_default_data()

	payload = []
	days = ScheduleDay.objects.prefetch_related("panels", "slots").all()
	for day in days:
		day_panels = [panel.name for panel in day.panels.all()]
		student_slots = [
			slot.label
			for slot in day.slots.all()
			if slot.role == Slot.ROLE_STUDENT
		]
		supervisor_slots = [
			slot.label
			for slot in day.slots.all()
			if slot.role == Slot.ROLE_SUPERVISOR
		]

		payload.append(
			{
				"date": day.date.isoformat(),
				"displayDate": day.date.strftime("%A %d %b"),
				"panels": day_panels,
				"studentSlots": student_slots,
				"supervisorSlots": supervisor_slots,
			}
		)

	return JsonResponse(payload, safe=False)


@require_http_methods(["GET", "POST", "DELETE"])
def bookings(request):
	ensure_default_data()

	if request.method == "GET":
		return JsonResponse(list_bookings(), safe=False)

	if request.method == "DELETE":
		deleted_count = clear_bookings()
		return JsonResponse({"deleted": deleted_count})

	try:
		payload = json.loads(request.body.decode("utf-8") or "{}")
	except json.JSONDecodeError:
		return JsonResponse({"message": "Invalid JSON payload."}, status=400)

	try:
		booking = create_booking(payload)
	except (BookingValidationError, BookingConflictError) as error:
		return JsonResponse({"message": str(error)}, status=400)

	return JsonResponse(booking, status=201)


@require_http_methods(["GET"])
def system_counts(request):
	ensure_default_data()
	return JsonResponse(get_system_counts())


def _normalize_header(value: str) -> str:
	return (value or "").strip().lower().replace(" ", "_")


def _column_value(row: dict, candidates: list[str]) -> str:
	for candidate in candidates:
		if candidate in row and row[candidate] is not None:
			return str(row[candidate]).strip()
	return ""


def _parse_csv(file_obj):
	wrapper = TextIOWrapper(file_obj, encoding="utf-8-sig")
	reader = csv.DictReader(wrapper)
	for raw_row in reader:
		yield {_normalize_header(key): value for key, value in raw_row.items()}


def _parse_xlsx(file_obj):
	workbook = load_workbook(file_obj, read_only=True, data_only=True)
	sheet = workbook.active
	headers = []
	for row_index, row in enumerate(sheet.iter_rows(values_only=True)):
		if row_index == 0:
			headers = [_normalize_header(str(value or "")) for value in row]
			continue

		yield {
			headers[index]: ("" if value is None else str(value).strip())
			for index, value in enumerate(row)
			if index < len(headers) and headers[index]
		}


@require_http_methods(["POST"])
def upload_supervisor_links(request):
	upload = request.FILES.get("file")
	if upload is None:
		return JsonResponse({"message": "Select an Excel or CSV file to upload."}, status=400)

	file_name = upload.name.lower()
	if not (file_name.endswith(".xlsx") or file_name.endswith(".csv")):
		return JsonResponse({"message": "Unsupported file type. Use .xlsx or .csv."}, status=400)

	if file_name.endswith(".csv"):
		rows = _parse_csv(upload.file)
	else:
		rows = _parse_xlsx(upload.file)

	supervisor_columns = ["supervisor", "supervisor_name", "supervisorname"]
	supervisor_email_columns = ["supervisor_email", "supervisoremail", "supervisor_mail"]
	student_columns = ["student", "student_name", "studentname"]
	student_email_columns = ["student_email", "studentemail", "student_mail"]

	pairs = []
	skipped = 0
	for row in rows:
		supervisor_name = _column_value(row, supervisor_columns)
		student_name = _column_value(row, student_columns)

		if not supervisor_name and not student_name:
			continue

		if not supervisor_name or not student_name:
			skipped += 1
			continue

		supervisor_email = _column_value(row, supervisor_email_columns)
		student_email = _column_value(row, student_email_columns)

		pairs.append((supervisor_name, supervisor_email, student_name, student_email))

	if not pairs:
		return JsonResponse(
			{"message": "No valid rows found. Required columns: supervisor and student."},
			status=400,
		)

	SupervisorStudentLink.objects.all().delete()

	seen = set()
	to_create = []
	for supervisor_name, supervisor_email, student_name, student_email in pairs:
		key = (supervisor_name.strip().lower(), student_name.strip().lower())
		if key in seen:
			continue
		seen.add(key)
		to_create.append(
			SupervisorStudentLink(
				supervisor_name=supervisor_name.strip(),
				supervisor_email=supervisor_email.strip().lower(),
				student_name=student_name.strip(),
				student_email=student_email.strip().lower(),
			)
		)

	SupervisorStudentLink.objects.bulk_create(to_create)

	return JsonResponse(
		{
			"inserted": len(to_create),
			"skipped": skipped,
			"counts": get_system_counts(),
		}
	)


@require_http_methods(["GET"])
def download_template(request):
	"""Serve the supervisor-student mapping template CSV."""
	template_path = Path(__file__).resolve().parent.parent / "supervisor_student_template.csv"
	if not template_path.exists():
		return JsonResponse({"message": "Template not found."}, status=404)
	return FileResponse(
		open(template_path, "rb"),
		as_attachment=True,
		filename="supervisor_student_template.csv",
		content_type="text/csv",
	)


@require_http_methods(["POST"])
def cancel_booking_view(request, booking_id):
	try:
		body = json.loads(request.body.decode("utf-8") or "{}")
	except json.JSONDecodeError:
		return JsonResponse({"message": "Invalid JSON."}, status=400)

	email = (body.get("email") or "").strip()
	reason = (body.get("reason") or "").strip()

	if not email:
		return JsonResponse({"message": "Email is required to cancel."}, status=400)

	try:
		updated = cancel_booking(booking_id, email, reason)
	except BookingValidationError as error:
		return JsonResponse({"message": str(error)}, status=400)
	except BookingConflictError as error:
		return JsonResponse({"message": str(error)}, status=403)

	return JsonResponse(updated)


@require_http_methods(["GET"])
def recommendations(request):
	ensure_default_data()

	supervisor_name = (request.GET.get("supervisor") or "").strip()
	date_value = (request.GET.get("date") or "").strip()
	panel_name = (request.GET.get("panel") or "").strip()
	if not supervisor_name or not date_value or not panel_name:
		return JsonResponse({"recommendations": []})

	day = ScheduleDay.objects.filter(date=date_value).first()
	panel = Panel.objects.filter(day=day, name=panel_name).first() if day else None
	if not day or not panel:
		return JsonResponse({"recommendations": []})

	slots = Slot.objects.filter(day=day, role=Slot.ROLE_SUPERVISOR).order_by("sort_order", "label")
	labels = recommend_supervisor_slots(supervisor_name, slots, day, panel)
	return JsonResponse({"recommendations": labels})


@require_http_methods(["GET"])
def search_supervisors(request):
	"""Search supervisors by name prefix. Returns list of {name, email}."""
	query = (request.GET.get("q") or "").strip().lower()
	if not query or len(query) < 2:
		return JsonResponse({"results": []})

	supervisors = Supervisor.objects.filter(name__icontains=query).order_by("name")[:20]
	results = [{"name": s.name, "email": s.email} for s in supervisors]
	return JsonResponse({"results": results})


@require_http_methods(["GET"])
def export_bookings(request):
	"""Export all active bookings as CSV."""
	from django.http import HttpResponse
	from Services.count import serialize_booking
	from booking_api.models import Booking

	bookings = Booking.objects.filter(status=Booking.STATUS_ACTIVE).order_by("-booked_at")
	
	response = HttpResponse(content_type="text/csv")
	response["Content-Disposition"] = 'attachment; filename="bookings_export.csv"'
	
	writer = csv.writer(response)
	writer.writerow(["First Name", "Surname", "Email", "Role", "Supervisor", "Co-Supervisor", "Date", "Panel", "Slot", "Booked At", "Status"])
	
	for booking in bookings:
		writer.writerow([
			booking.first_name,
			booking.surname,
			booking.email,
			booking.role,
			booking.supervisor,
			booking.co_supervisor,
			booking.day.date.isoformat(),
			booking.panel.name,
			booking.slot.label,
			booking.booked_at.isoformat(),
			booking.status,
		])
	
	return response
