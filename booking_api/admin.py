import csv
from io import TextIOWrapper

from django.contrib import admin, messages
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path
from openpyxl import load_workbook

from booking_api.models import Booking, Panel, ScheduleDay, Slot, SupervisorStudentLink, Supervisor


def _normalize_header(value):
    return (value or "").strip().lower().replace(" ", "_")


def _column_value(row, candidates):
    for key in candidates:
        if key in row and row[key] is not None and str(row[key]).strip():
            return str(row[key]).strip()
    return ""


def _rows_from_xlsx(file_obj):
    workbook = load_workbook(file_obj, read_only=True, data_only=True)
    sheet = workbook.active
    headers = []
    for row_index, row in enumerate(sheet.iter_rows(values_only=True)):
        if row_index == 0:
            headers = [_normalize_header(str(v or "")) for v in row]
            continue
        yield {
            headers[i]: ("" if v is None else str(v).strip())
            for i, v in enumerate(row)
            if i < len(headers) and headers[i]
        }


def _rows_from_csv(file_obj):
    wrapper = TextIOWrapper(file_obj, encoding="utf-8-sig")
    reader = csv.DictReader(wrapper)
    for raw in reader:
        yield {_normalize_header(k): v for k, v in raw.items()}


@admin.register(ScheduleDay)
class ScheduleDayAdmin(admin.ModelAdmin):
    list_display = ("id", "date")


@admin.register(Panel)
class PanelAdmin(admin.ModelAdmin):
    list_display = ("id", "day", "name")
    list_filter = ("day",)


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ("id", "day", "role", "label", "sort_order")
    list_filter = ("day", "role")


@admin.register(SupervisorStudentLink)
class SupervisorStudentLinkAdmin(admin.ModelAdmin):
    list_display = ("id", "supervisor_name", "supervisor_email", "student_name", "student_email")
    search_fields = ("supervisor_name", "supervisor_email", "student_name", "student_email")
    changelist_template = "admin/booking_api/supervisorstudentlink/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path(
                "upload-excel/",
                self.admin_site.admin_view(self.upload_excel_view),
                name="booking_api_supervisorstudentlink_upload_excel",
            ),
        ]
        return extra + urls

    def upload_excel_view(self, request):
        if request.method == "POST":
            upload = request.FILES.get("file")
            if not upload:
                self.message_user(request, "No file selected.", level=messages.ERROR)
                return redirect("..")

            name = upload.name.lower()
            if not (name.endswith(".xlsx") or name.endswith(".csv")):
                self.message_user(request, "Use .xlsx or .csv only.", level=messages.ERROR)
                return redirect("..")

            rows = list(_rows_from_xlsx(upload.file) if name.endswith(".xlsx") else _rows_from_csv(upload.file))

            sup_cols = ["supervisor", "supervisor_name", "supervisorname"]
            stu_cols = ["student", "student_name", "studentname"]

            seen, to_create, skipped = set(), [], 0
            for row in rows:
                sup = _column_value(row, sup_cols)
                stu = _column_value(row, stu_cols)
                if not sup and not stu:
                    continue
                if not sup or not stu:
                    skipped += 1
                    continue
                key = (sup.lower(), stu.lower())
                if key in seen:
                    continue
                seen.add(key)
                to_create.append(SupervisorStudentLink(supervisor_name=sup, student_name=stu))

            if not to_create:
                self.message_user(
                    request,
                    "No valid rows found. Required columns: supervisor and student.",
                    level=messages.ERROR,
                )
                return redirect("..")

            SupervisorStudentLink.objects.all().delete()
            SupervisorStudentLink.objects.bulk_create(to_create)

            msg = f"Import complete: {len(to_create)} mappings loaded."
            if skipped:
                msg += f" {skipped} incomplete rows skipped."
            self.message_user(request, msg, level=messages.SUCCESS)
            return redirect("..")

        context = {
            **self.admin_site.each_context(request),
            "title": "Upload Supervisor-Student Mapping",
            "opts": self.model._meta,
        }
        return TemplateResponse(
            request,
            "admin/booking_api/supervisorstudentlink/upload_excel.html",
            context,
        )


@admin.register(Supervisor)
class SupervisorAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "email")
	search_fields = ("name", "email")
	ordering = ("name",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
	list_display = ("id", "first_name", "surname", "email", "role", "supervisor", "get_co_supervisor", "day", "panel", "slot", "status", "booked_at")
	list_filter = ("day", "role", "panel", "status")
	search_fields = ("first_name", "surname", "email", "supervisor", "co_supervisor")
	readonly_fields = ("booked_at", "cancelled_at")

	def get_co_supervisor(self, obj):
		return obj.co_supervisor if hasattr(obj, 'co_supervisor') else ""
	get_co_supervisor.short_description = "Co-Supervisor"
