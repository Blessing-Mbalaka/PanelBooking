"""Django management command to populate the Supervisor table."""

import csv
import sys
from django.core.management.base import BaseCommand, CommandError
from booking_api.models import Supervisor, SupervisorStudentLink


class Command(BaseCommand):
	help = "Populate supervisor database. Options: 'extract' (from links), 'add' (interactive), 'clear', 'load_csv' (from file)"

	def add_arguments(self, parser):
		parser.add_argument(
			"action",
			nargs="?",
			default="extract",
			type=str,
			choices=["extract", "add", "clear", "load_csv"],
			help="Action to perform: extract (from SupervisorStudentLink), add (manual entry), clear (delete all), load_csv (from file)",
		)
		parser.add_argument(
			"--file",
			type=str,
			help="CSV file path (required for load_csv action)",
		)

	def handle(self, *args, **options):
		action = options["action"]

		if action == "clear":
			count, _ = Supervisor.objects.all().delete()
			self.stdout.write(
				self.style.SUCCESS(f"Deleted {count} supervisors.")
			)
			return

		if action == "extract":
			self.extract_from_links()
			return

		if action == "add":
			self.add_supervisors_interactive()
			return

		if action == "load_csv":
			if not options.get("file"):
				raise CommandError("--file argument required for load_csv action")
			self.load_from_csv(options["file"])
			return

	def extract_from_links(self):
		"""Extract unique supervisor names from SupervisorStudentLink and populate Supervisor table."""
		links = SupervisorStudentLink.objects.values_list(
			"supervisor_name", "supervisor_email"
		).distinct()

		existing = set(Supervisor.objects.values_list("name", flat=True).lower())
		created_count = 0

		for supervisor_name, supervisor_email in links:
			supervisor_name = (supervisor_name or "").strip()
			supervisor_email = (supervisor_email or "").strip().lower()

			if not supervisor_name:
				continue

			if supervisor_name.lower() not in existing:
				Supervisor.objects.create(name=supervisor_name, email=supervisor_email)
				created_count += 1
				self.stdout.write(f"  + {supervisor_name}")

		self.stdout.write(
			self.style.SUCCESS(f"Created {created_count} supervisors from SupervisorStudentLink.")
		)

	def add_supervisors_interactive(self):
		"""Interactively add supervisors one by one."""
		self.stdout.write("Enter supervisor names and emails (empty name to finish):")
		created_count = 0

		while True:
			name = input("Supervisor name: ").strip()
			if not name:
				break
			email = input(f"Email for {name} (optional): ").strip().lower()

			existing = Supervisor.objects.filter(name__iexact=name).first()
			if existing:
				self.stdout.write(self.style.WARNING(f"  Supervisor '{name}' already exists."))
				continue

			Supervisor.objects.create(name=name, email=email)
			created_count += 1
			self.stdout.write(self.style.SUCCESS(f"  ✓ Added {name}"))

		self.stdout.write(
			self.style.SUCCESS(f"Created {created_count} supervisors.")
		)

	def load_from_csv(self, file_path):
		"""Load supervisor-student mapping from CSV file and populate both tables."""
		try:
			with open(file_path, "r", encoding="utf-8") as f:
				reader = csv.DictReader(f)
				if not reader.fieldnames:
					raise CommandError("CSV file is empty or has no headers.")

				# Normalize field names (accept variations)
				fieldnames_lower = [fn.lower().strip() if fn else "" for fn in reader.fieldnames]

				# Find supervisor and student columns (flexible naming)
				supervisor_idx = next(
					(i for i, fn in enumerate(fieldnames_lower) if "supervisor" in fn and "email" not in fn),
					None
				)
				supervisor_email_idx = next(
					(i for i, fn in enumerate(fieldnames_lower) if "supervisor" in fn and "email" in fn),
					None
				)
				student_idx = next(
					(i for i, fn in enumerate(fieldnames_lower) if "student" in fn and "email" not in fn),
					None
				)
				student_email_idx = next(
					(i for i, fn in enumerate(fieldnames_lower) if "student" in fn and "email" in fn),
					None
				)

				if supervisor_idx is None or student_idx is None:
					raise CommandError(
						f"CSV must have 'supervisor' and 'student' columns. Found: {reader.fieldnames}"
					)

				original_fieldnames = reader.fieldnames
				supervisor_col = original_fieldnames[supervisor_idx]
				student_col = original_fieldnames[student_idx]
				supervisor_email_col = original_fieldnames[supervisor_email_idx] if supervisor_email_idx is not None else None
				student_email_col = original_fieldnames[student_email_idx] if student_email_idx is not None else None

				supervisor_set = set()
				link_set = set()
				row_count = 0
				error_rows = []

				for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
					supervisor_name = (row.get(supervisor_col) or "").strip()
					student_name = (row.get(student_col) or "").strip()
					supervisor_email = (row.get(supervisor_email_col) or "").strip().lower() if supervisor_email_col else ""
					student_email = (row.get(student_email_col) or "").strip().lower() if student_email_col else ""

					if not supervisor_name or not student_name:
						error_rows.append(f"Row {row_num}: Missing supervisor or student name")
						continue

					supervisor_set.add((supervisor_name, supervisor_email))
					link_set.add((supervisor_name, supervisor_email, student_name, student_email))
					row_count += 1

				if error_rows:
					self.stdout.write(self.style.WARNING("Warnings:"))
					for err in error_rows:
						self.stdout.write(f"  {err}")

				# Clear existing data
				SupervisorStudentLink.objects.all().delete()
				self.stdout.write("Cleared existing SupervisorStudentLink records.")

				# Load SupervisorStudentLink
				link_count = 0
				for supervisor_name, supervisor_email, student_name, student_email in link_set:
					SupervisorStudentLink.objects.create(
						supervisor_name=supervisor_name,
						supervisor_email=supervisor_email,
						student_name=student_name,
						student_email=student_email,
					)
					link_count += 1

				self.stdout.write(
					self.style.SUCCESS(f"Created {link_count} supervisor-student links.")
				)

				# Extract unique supervisors and populate Supervisor table
				Supervisor.objects.all().delete()
				self.stdout.write("Cleared existing Supervisor records.")

				supervisor_count = 0
				for supervisor_name, supervisor_email in supervisor_set:
					Supervisor.objects.create(
						name=supervisor_name,
						email=supervisor_email,
					)
					supervisor_count += 1
					self.stdout.write(f"  + {supervisor_name}")

				self.stdout.write(
					self.style.SUCCESS(f"Loaded {supervisor_count} supervisors and {link_count} student mappings from {file_path}.")
				)

		except FileNotFoundError:
			raise CommandError(f"File not found: {file_path}")
		except Exception as e:
			raise CommandError(f"Error reading CSV: {str(e)}")
