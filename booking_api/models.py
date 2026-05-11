from django.db import models


class ScheduleDay(models.Model):
	date = models.DateField(unique=True)

	class Meta:
		ordering = ["date"]

	def __str__(self):
		return self.date.isoformat()


class Panel(models.Model):
	day = models.ForeignKey(ScheduleDay, on_delete=models.CASCADE, related_name="panels")
	name = models.CharField(max_length=100)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["day", "name"], name="unique_panel_per_day"),
		]
		ordering = ["day__date", "name"]

	def __str__(self):
		return f"{self.day.date} - {self.name}"


class Slot(models.Model):
	ROLE_STUDENT = "student"
	ROLE_SUPERVISOR = "supervisor"
	ROLE_CHOICES = [
		(ROLE_STUDENT, "Student"),
		(ROLE_SUPERVISOR, "Supervisor"),
	]

	day = models.ForeignKey(ScheduleDay, on_delete=models.CASCADE, related_name="slots")
	role = models.CharField(max_length=20, choices=ROLE_CHOICES)
	label = models.CharField(max_length=100)
	sort_order = models.PositiveIntegerField(default=0)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["day", "role", "label"], name="unique_slot_per_day_role"),
		]
		ordering = ["day__date", "role", "sort_order", "label"]

	def __str__(self):
		return f"{self.day.date} - {self.role} - {self.label}"


class SupervisorStudentLink(models.Model):
	supervisor_name = models.CharField(max_length=255)
	supervisor_email = models.EmailField(max_length=254, blank=True, default="")
	student_name = models.CharField(max_length=255)
	student_email = models.EmailField(max_length=254, blank=True, default="")

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=["supervisor_name", "student_name"],
				name="unique_supervisor_student_link",
			),
		]
		ordering = ["supervisor_name", "student_name"]

	def __str__(self):
		return f"{self.supervisor_name} supervises {self.student_name}"


class Supervisor(models.Model):
	name = models.CharField(max_length=255, unique=True)
	email = models.EmailField(max_length=254, blank=True, default="")

	class Meta:
		ordering = ["name"]

	def __str__(self):
		return self.name


class Booking(models.Model):
	ROLE_STUDENT = Slot.ROLE_STUDENT
	ROLE_SUPERVISOR = Slot.ROLE_SUPERVISOR
	ROLE_CHOICES = Slot.ROLE_CHOICES

	STATUS_ACTIVE = "active"
	STATUS_CANCELLED = "cancelled"
	STATUS_CHOICES = [
		(STATUS_ACTIVE, "Active"),
		(STATUS_CANCELLED, "Cancelled"),
	]

	first_name = models.CharField(max_length=150)
	surname = models.CharField(max_length=150)
	email = models.EmailField(max_length=254)
	role = models.CharField(max_length=20, choices=ROLE_CHOICES)
	supervisor = models.CharField(max_length=255, blank=True, default="")
	co_supervisor = models.CharField(max_length=255, blank=True, default="")  # Co-supervisor
	day = models.ForeignKey(ScheduleDay, on_delete=models.CASCADE, related_name="bookings")
	panel = models.ForeignKey(Panel, on_delete=models.CASCADE, related_name="bookings")
	slot = models.ForeignKey(Slot, on_delete=models.CASCADE, related_name="bookings")
	booked_at = models.DateTimeField(auto_now_add=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
	cancellation_reason = models.TextField(blank=True, default="")
	cancelled_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=["day", "panel", "role", "slot"],
				name="unique_slot_booking",
				condition=models.Q(status="active"),
			),
		]
		ordering = ["-booked_at"]

	@property
	def full_name(self):
		return f"{self.first_name} {self.surname}"

	def __str__(self):
		return f"{self.full_name} ({self.role}) {self.day.date} {self.panel.name} {self.slot.label}"
