const API_BASE = "/api";

let scheduleConfig = [];
let bookings = [];
let systemCounts = { students: 0, supervisors: 0 };

const firstNameInput = document.getElementById("firstName");
const surnameInput = document.getElementById("surname");
const emailInput = document.getElementById("email");
const roleSelect = document.getElementById("role");
const supervisor = document.getElementById("supervisor");
const supervisorFieldContainer = document.getElementById("supervisorFieldContainer");
const supervisorName = document.getElementById("supervisorName");
const dateSelect = document.getElementById("date");
const panelSelect = document.getElementById("panel");
const slotSelect = document.getElementById("slot");
const slotLabel = document.getElementById("slotLabel");
const bookButton = document.getElementById("bookButton");
const messageBox = document.getElementById("message");
const cancelMessageBox = document.getElementById("cancelMessage");
let bookingSubmissionInFlight = false;

async function apiFetch(path, options) {
  const response = await fetch(API_BASE + path, options || {});
  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await response.json() : {};

  if (!response.ok) {
    const message = payload.message || "Request failed.";
    throw new Error(message);
  }

  return payload;
}

function getCsrfToken() {
  const cookie = document.cookie
    .split(";")
    .map(function (entry) {
      return entry.trim();
    })
    .find(function (entry) {
      return entry.startsWith("csrftoken=");
    });

  return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
}

async function startApp() {
  try {
    await refreshData();
    loadDates();
    loadPanels();
    loadSlots();
    renderSchedule();
  } catch (error) {
    showMessage(error.message || "Failed to load data.", "error");
  }

  supervisorFieldContainer.style.display = "block";

  dateSelect.addEventListener("change", function () {
    loadPanels();
    loadSlots();
  });

  panelSelect.addEventListener("change", loadSlots);
  
  roleSelect.addEventListener("change", function () {
    loadSlots();
  });
}

async function refreshData() {
  const data = await Promise.all([
    apiFetch("/schedule/"),
    apiFetch("/bookings/"),
    apiFetch("/system-counts/"),
  ]);
  scheduleConfig = data[0];
  bookings = data[1];
  systemCounts = data[2];
  renderSystemCounts();
}

function renderSystemCounts() {
  document.getElementById("systemStudents").textContent = systemCounts.students;
  document.getElementById("systemSupervisors").textContent = systemCounts.supervisors;
}

function getSelectedDay() {
  return scheduleConfig.find(function (day) {
    return day.date === dateSelect.value;
  }) || scheduleConfig[0];
}

function loadDates() {
  dateSelect.innerHTML = "";
  scheduleConfig.forEach(function (day) {
    const option = document.createElement("option");
    option.value = day.date;
    option.textContent = day.displayDate;
    dateSelect.appendChild(option);
  });
}

function loadPanels() {
  const day = getSelectedDay();
  panelSelect.innerHTML = "";
  if (!day) {
    return;
  }

  day.panels.forEach(function (panel) {
    const option = document.createElement("option");
    option.value = panel;
    option.textContent = panel;
    panelSelect.appendChild(option);
  });
}

function loadSlots() {
  const day = getSelectedDay();
  if (!day) {
    slotSelect.innerHTML = "";
    return;
  }

  const role = roleSelect.value;
  const panel = panelSelect.value;
  const slots = role === "student" ? day.studentSlots : day.supervisorSlots;

  slotLabel.textContent = role === "student" ? "Time" : "Slot";
  slotSelect.innerHTML = "";

  slots.forEach(function (slot) {
    const option = document.createElement("option");
    option.value = slot;

    if (slotIsTaken(day.date, panel, role, slot)) {
      option.textContent = slot + " • Taken";
      option.disabled = true;
    } else {
      option.textContent = slot;
    }

    slotSelect.appendChild(option);
  });
}

function slotIsTaken(date, panel, role, slot) {
  return bookings.some(function (booking) {
    return booking.date === date && booking.panel === panel && booking.role === role && booking.slot === slot;
  });
}

async function bookSlot() {
  if (bookingSubmissionInFlight) {
    console.warn("Duplicate booking submit ignored.");
    return;
  }

  const supervisorValue = supervisor.value.trim();
  if (!supervisorValue) {
    showMessage("Please fill in the supervisor field before booking.", "error");
    supervisor.focus();
    return;
  }

  const day = getSelectedDay();
  const payload = {
    firstName: firstNameInput.value.trim(),
    surname: surnameInput.value.trim(),
    email: emailInput.value.trim(),
    role: roleSelect.value,
    supervisor: supervisorValue,
    coSupervisorName: supervisorName.value.trim(),
    date: day ? day.date : "",
    panel: panelSelect.value,
    slot: slotSelect.value,
  };

  bookingSubmissionInFlight = true;
  if (bookButton) {
    bookButton.disabled = true;
    bookButton.textContent = "Booking...";
  }

  try {
    console.debug("Submitting booking", payload);
    await apiFetch("/bookings/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(payload),
    });

    await refreshData();
    firstNameInput.value = "";
    surnameInput.value = "";
    emailInput.value = "";
    supervisor.value = "";
    supervisorName.value = "";
    showMessage("Booking confirmed.", "success");
    loadSlots();
    renderSchedule();
  } catch (error) {
    showMessage(error.message || "Booking failed.", "error");
    loadSlots();
  } finally {
    bookingSubmissionInFlight = false;
    if (bookButton) {
      bookButton.disabled = false;
      bookButton.textContent = "Confirm Booking";
    }
  }
}

function getBooking(date, panel, role, slot) {
  return bookings.find(function (booking) {
    return booking.date === date && booking.panel === panel && booking.role === role && booking.slot === slot;
  });
}

function countBookings(date, panel, role) {
  return bookings.filter(function (booking) {
    return booking.date === date && booking.panel === panel && booking.role === role;
  }).length;
}

function renderSchedule() {
  const scheduleDiv = document.getElementById("schedule");
  scheduleDiv.innerHTML = "";

  let totalStudents = 0;
  let totalSupervisors = 0;

  scheduleConfig.forEach(function (day) {
    const daySection = document.createElement("div");
    daySection.className = "day-section";

    const dayTitle = document.createElement("div");
    dayTitle.className = "day-title";
    dayTitle.innerHTML = "<span>" + day.displayDate + "</span><span>Fixed Slots</span>";
    daySection.appendChild(dayTitle);

    const panelGrid = document.createElement("div");
    panelGrid.className = "panel-grid";

    day.panels.forEach(function (panel) {
      const studentCount = countBookings(day.date, panel, "student");
      const supervisorCount = countBookings(day.date, panel, "supervisor");
      totalStudents += studentCount;
      totalSupervisors += supervisorCount;

      const isFull = studentCount === day.studentSlots.length && supervisorCount === day.supervisorSlots.length;
      const panelCard = document.createElement("div");
      panelCard.className = isFull ? "panel-card full" : "panel-card";

      let studentRows = "";
      day.studentSlots.forEach(function (slot) {
        const booking = getBooking(day.date, panel, "student", slot);
        studentRows += "<div class='slot-row'><strong>" + slot + "</strong><br>" + (booking ? (booking.firstName + " " + booking.surname) : "<span class='empty'>Open</span>") + "</div>";
      });

      let supervisorRows = "";
      day.supervisorSlots.forEach(function (slot) {
        const booking = getBooking(day.date, panel, "supervisor", slot);
        supervisorRows += "<div class='slot-row'><strong>" + slot + "</strong><br>" + (booking ? (booking.firstName + " " + booking.surname) : "<span class='empty'>Open</span>") + "</div>";
      });

      panelCard.innerHTML =
        "<div class='panel-top'>" +
          "<h3>" + panel + "</h3>" +
          "<span class='badge " + (isFull ? "full-badge" : "open-badge") + "'>" + (isFull ? "Full" : "Open") + "</span>" +
        "</div>" +
        "<div class='counts'>" +
          "<div class='count-box'><strong>" + studentCount + "/" + day.studentSlots.length + "</strong>Students</div>" +
          "<div class='count-box'><strong>" + supervisorCount + "/" + day.supervisorSlots.length + "</strong>Sup.</div>" +
        "</div>" +
        "<div class='list'>" +
          "<div class='list-title'>Students</div>" + studentRows +
          "<div class='list-title'>Supervisors</div>" + supervisorRows +
        "</div>";

      panelGrid.appendChild(panelCard);
    });

    daySection.appendChild(panelGrid);
    scheduleDiv.appendChild(daySection);
  });

  const studentCapacity = Math.max(systemCounts.students, totalStudents);
  const supervisorCapacity = Math.max(systemCounts.supervisors, totalSupervisors);
  document.getElementById("totalStudents").textContent = totalStudents + "/" + studentCapacity;
  document.getElementById("totalSupervisors").textContent = totalSupervisors + "/" + supervisorCapacity;
}

function showMessage(text, type) {
  messageBox.textContent = text;
  messageBox.className = "message " + type;
}
function showCancelMessage(text, type) {
  cancelMessageBox.textContent = text;
  cancelMessageBox.className = "message " + (type || "");
}
function downloadCSV() {
  if (bookings.length === 0) {
    showMessage("No bookings.", "error");
    return;
  }

  const headers = ["First Name", "Surname", "Email", "Role", "Supervisor", "Co-Supervisor", "Date", "Panel", "Slot", "Status", "Booked At"];
  const rows = bookings.map(function (booking) {
    return [
      booking.firstName, booking.surname, booking.email,
      booking.role, booking.supervisor, booking.supervisorName,
      booking.dateDisplay || booking.date,
      booking.panel, booking.slot, booking.status, booking.bookedAt
    ];
  });

  const csvContent = [headers].concat(rows).map(function (row) {
    return row.map(function (value) {
      return '"' + value + '"';
    }).join(",");
  }).join("\n");

  const blob = new Blob([csvContent], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "panel_presentation_bookings.csv";
  link.click();
  URL.revokeObjectURL(url);
}

async function resetBookings() {
  const confirmReset = confirm("Delete all bookings?");
  if (!confirmReset) {
    return;
  }

  try {
    await apiFetch("/bookings/", {
      method: "DELETE",
      headers: {
        "X-CSRFToken": getCsrfToken(),
      },
    });

    await refreshData();
    showMessage("Cleared.", "success");
    loadSlots();
    renderSchedule();
  } catch (error) {
    showMessage(error.message || "Clear failed.", "error");
  }
}

async function lookupAndCancel() {
  const email = (document.getElementById("cancelEmail").value || "").trim();
  const reason = (document.getElementById("cancelReason").value || "").trim();

  if (!email) {
    showCancelMessage("Enter your booking email.", "error");
    return;
  }
  if (!reason) {
    showCancelMessage("Provide a reason for cancellation.", "error");
    return;
  }

  // Find the active booking matching this email
  const match = bookings.find(function (b) {
    return b.email.toLowerCase() === email.toLowerCase() && b.status === "active";
  });

  if (!match) {
    showCancelMessage("No active booking found for that email.", "error");
    return;
  }

  try {
    await apiFetch("/bookings/" + match.id + "/cancel/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({ email: email, reason: reason }),
    });

    await refreshData();
    document.getElementById("cancelEmail").value = "";
    document.getElementById("cancelReason").value = "";
    showCancelMessage("Booking cancelled successfully.", "success");
    loadSlots();
    renderSchedule();
  } catch (error) {
    showCancelMessage(error.message || "Cancellation failed.", "error");
  }
}

window.bookSlot = bookSlot;
window.downloadCSV = downloadCSV;
window.resetBookings = resetBookings;
window.lookupAndCancel = lookupAndCancel;

document.addEventListener("DOMContentLoaded", startApp);
