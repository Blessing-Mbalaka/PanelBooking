const API_BASE = "/api";
const bookingType = document.body.dataset.bookingType || "syndicate";

let scheduleConfig = [];
let bookings = [];
let systemCounts = { students: 0, supervisors: 0 };
let bookingSubmissionInFlight = false;
let settingsPassword = "";
let editingDateValue = "";
const fallbackPanels = ["Panel 1", "Panel 2", "Panel 3", "Panel 4"];
const fallbackStudentSlots = [
  "10:00 - 10:30",
  "10:30 - 11:00",
  "11:00 - 11:30",
  "11:30 - 12:00",
  "12:30 - 13:00",
];

const firstNameInput = document.getElementById("firstName");
const surnameInput = document.getElementById("surname");
const emailInput = document.getElementById("email");
const dateSelect = document.getElementById("date");
const panelSelect = document.getElementById("panel");
const slotSelect = document.getElementById("slot");
const slotLabel = document.getElementById("slotLabel");
const bookButton = document.getElementById("bookButton");
const printButton = document.getElementById("printButton");
const messageBox = document.getElementById("message");
const settingsButton = document.getElementById("settingsButton");
const settingsPanel = document.getElementById("settingsPanel");
const settingsPasswordInput = document.getElementById("settingsPassword");
const unlockSettingsButton = document.getElementById("unlockSettingsButton");
const settingsLocked = document.getElementById("settingsLocked");
const settingsManager = document.getElementById("settingsManager");
const scheduleDateInput = document.getElementById("scheduleDateInput");
const openDateEditorButton = document.getElementById("openDateEditorButton");
const settingsDatesList = document.getElementById("settingsDatesList");
const activeBookingsList = document.getElementById("activeBookingsList");
const settingsMessageBox = document.getElementById("settingsMessage");
const dateEditorModal = document.getElementById("dateEditorModal");
const dateEditorSubtitle = document.getElementById("dateEditorSubtitle");
const closeDateEditorButton = document.getElementById("closeDateEditorButton");
const dateEditorMessage = document.getElementById("dateEditorMessage");
const panelEditorList = document.getElementById("panelEditorList");
const slotEditorList = document.getElementById("slotEditorList");
const addPanelButton = document.getElementById("addPanelButton");
const addSlotButton = document.getElementById("addSlotButton");
const autofillSlotsButton = document.getElementById("autofillSlotsButton");
const sortPanelsButton = document.getElementById("sortPanelsButton");
const sortSlotsButton = document.getElementById("sortSlotsButton");
const saveDateConfigButton = document.getElementById("saveDateConfigButton");
const toastStack = document.getElementById("toastStack");
let dragState = null;

async function apiFetch(path, options) {
  const response = await fetch(API_BASE + path, options || {});
  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await response.json() : {};

  if (!response.ok) {
    throw new Error(payload.message || "Request failed.");
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
  bindEvents();

  try {
    await refreshData();
    hydrateBookingUi();
    renderSchedule();
    renderConfiguredDates();
  } catch (error) {
    showMessage(error.message || "Failed to load data.", "error");
  }
}

function bindEvents() {
  dateSelect.addEventListener("change", function () {
    loadPanels();
    loadSlots();
  });

  panelSelect.addEventListener("change", loadSlots);
  if (printButton) {
    printButton.addEventListener("click", function () {
      window.print();
    });
  }
  settingsButton.addEventListener("click", toggleSettingsPanel);
  unlockSettingsButton.addEventListener("click", unlockSettings);
  openDateEditorButton.addEventListener("click", function () {
    openDateEditor(scheduleDateInput.value);
  });
  scheduleDateInput.addEventListener("change", function () {
    if (settingsPassword) {
      openDateEditorButton.textContent = getScheduleDayByDate(scheduleDateInput.value) ? "Open Editor" : "Create Date";
    }
  });
  closeDateEditorButton.addEventListener("click", closeDateEditor);
  addPanelButton.addEventListener("click", function () {
    addPanelEditorRow("");
  });
  addSlotButton.addEventListener("click", function () {
    addSlotEditorRow("", "");
  });
  autofillSlotsButton.addEventListener("click", autofillHalfHourSlots);
  sortPanelsButton.addEventListener("click", sortPanelEditorRows);
  sortSlotsButton.addEventListener("click", sortSlotEditorRows);
  saveDateConfigButton.addEventListener("click", saveDateConfigurationFromModal);
  dateEditorModal.addEventListener("click", function (event) {
    if (event.target === dateEditorModal) {
      closeDateEditor();
    }
  });
}

async function refreshData() {
  const data = await Promise.all([
    apiFetch("/schedule/?bookingType=" + encodeURIComponent(bookingType)),
    apiFetch("/bookings/?bookingType=" + encodeURIComponent(bookingType)),
    apiFetch("/system-counts/"),
  ]);

  scheduleConfig = data[0];
  bookings = data[1];
  systemCounts = data[2];
  renderSystemCounts();
}

function hydrateBookingUi() {
  loadDates();
  loadPanels();
  loadSlots();
}

function renderSystemCounts() {
  document.getElementById("systemStudents").textContent = systemCounts.students;
  document.getElementById("configuredDatesCount").textContent = scheduleConfig.length;
  document.getElementById("totalDates").textContent = scheduleConfig.length;
}

function getSelectedDay() {
  return scheduleConfig.find(function (day) {
    return day.date === dateSelect.value;
  }) || scheduleConfig[0] || null;
}

function loadDates() {
  const previousValue = dateSelect.value;
  dateSelect.innerHTML = "";

  scheduleConfig.forEach(function (day) {
    const option = document.createElement("option");
    option.value = day.date;
    option.textContent = day.displayDate;
    dateSelect.appendChild(option);
  });

  if (scheduleConfig.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No dates configured";
    dateSelect.appendChild(option);
    dateSelect.disabled = true;
    bookButton.disabled = true;
    return;
  }

  dateSelect.disabled = false;
  bookButton.disabled = false;
  if (previousValue && scheduleConfig.some(function (day) { return day.date === previousValue; })) {
    dateSelect.value = previousValue;
  }
}

function loadPanels() {
  const day = getSelectedDay();
  panelSelect.innerHTML = "";

  if (!day) {
    panelSelect.disabled = true;
    return;
  }

  panelSelect.disabled = false;
  day.panels.forEach(function (panel) {
    const option = document.createElement("option");
    option.value = panel;
    option.textContent = panel;
    panelSelect.appendChild(option);
  });
}

function loadSlots() {
  const day = getSelectedDay();
  slotLabel.textContent = "Time";
  slotSelect.innerHTML = "";

  if (!day) {
    slotSelect.disabled = true;
    return;
  }

  const panel = panelSelect.value;
  slotSelect.disabled = false;

  day.studentSlots.forEach(function (slot) {
    const option = document.createElement("option");
    option.value = slot;

    if (slotIsTaken(day.date, panel, slot)) {
      option.textContent = slot + " • Taken";
      option.disabled = true;
    } else {
      option.textContent = slot;
    }

    slotSelect.appendChild(option);
  });
}

function slotIsTaken(date, panel, slot) {
  return bookings.some(function (booking) {
    return booking.date === date && booking.panel === panel && booking.role === "student" && booking.slot === slot;
  });
}

async function bookSlot() {
  if (bookingSubmissionInFlight) {
    return;
  }

  const day = getSelectedDay();
  if (!day) {
    showMessage("No booking dates are available yet.", "error");
    return;
  }

  const payload = {
    firstName: firstNameInput.value.trim(),
    surname: surnameInput.value.trim(),
    email: emailInput.value.trim(),
    bookingType: bookingType,
    role: "student",
    supervisor: "",
    coSupervisorName: "",
    date: day.date,
    panel: panelSelect.value,
    slot: slotSelect.value,
  };

  bookingSubmissionInFlight = true;
  bookButton.disabled = true;
  bookButton.textContent = "Booking...";

  try {
    await apiFetch("/bookings/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(payload),
    });

    await refreshData();
    hydrateBookingUi();
    renderSchedule();
    firstNameInput.value = "";
    surnameInput.value = "";
    emailInput.value = "";
    showMessage("Booking confirmed.", "success");
  } catch (error) {
    showMessage(error.message || "Booking failed.", "error");
    loadSlots();
  } finally {
    bookingSubmissionInFlight = false;
    bookButton.disabled = scheduleConfig.length === 0;
    bookButton.textContent = "Confirm Booking";
  }
}

function getBooking(date, panel, slot) {
  return bookings.find(function (booking) {
    return booking.date === date && booking.panel === panel && booking.role === "student" && booking.slot === slot;
  });
}

function countBookings(date, panel) {
  return bookings.filter(function (booking) {
    return booking.date === date && booking.panel === panel && booking.role === "student";
  }).length;
}

function renderSchedule() {
  const scheduleDiv = document.getElementById("schedule");
  scheduleDiv.innerHTML = "";

  let totalStudents = 0;

  scheduleConfig.forEach(function (day) {
    const daySection = document.createElement("div");
    daySection.className = "day-section";

    const dayTitle = document.createElement("div");
    dayTitle.className = "day-title";
    dayTitle.innerHTML = "<span>" + day.displayDate + "</span><span>Student Booking Slots</span>";
    daySection.appendChild(dayTitle);

    const panelGrid = document.createElement("div");
    panelGrid.className = "panel-grid";

    day.panels.forEach(function (panel) {
      const studentCount = countBookings(day.date, panel);
      totalStudents += studentCount;

      const isFull = studentCount === day.studentSlots.length;
      const panelCard = document.createElement("div");
      panelCard.className = isFull ? "panel-card full" : "panel-card";

      let studentRows = "";
      day.studentSlots.forEach(function (slot) {
        const booking = getBooking(day.date, panel, slot);
        studentRows += "<div class='slot-row'><strong>" + slot + "</strong><br>" + (booking ? (booking.firstName + " " + booking.surname) : "<span class='empty'>Open</span>") + "</div>";
      });

      panelCard.innerHTML =
        "<div class='panel-top'>" +
          "<h3>" + panel + "</h3>" +
          "<span class='badge " + (isFull ? "full-badge" : "open-badge") + "'>" + (isFull ? "Full" : "Open") + "</span>" +
        "</div>" +
        "<div class='counts'>" +
          "<div class='count-box'><strong>" + studentCount + "/" + day.studentSlots.length + "</strong>Students</div>" +
          "<div class='count-box'><strong>" + day.studentSlots.length + "</strong>Slots</div>" +
        "</div>" +
        "<div class='list'>" +
          "<div class='list-title'>Students</div>" + studentRows +
        "</div>";

      panelGrid.appendChild(panelCard);
    });

    daySection.appendChild(panelGrid);
    scheduleDiv.appendChild(daySection);
  });

  const studentCapacity = Math.max(systemCounts.students, totalStudents, 0);
  document.getElementById("totalStudents").textContent = totalStudents + "/" + studentCapacity;
}

function toggleSettingsPanel() {
  settingsPanel.classList.toggle("hidden");
  if (!settingsPanel.classList.contains("hidden") && settingsPassword) {
    openDateEditorButton.textContent = getScheduleDayByDate(scheduleDateInput.value) ? "Open Editor" : "Create Date";
  }
}

async function unlockSettings() {
  try {
    await apiFetch("/settings/unlock/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({ password: settingsPasswordInput.value.trim() }),
    });

    settingsPassword = settingsPasswordInput.value.trim();
    settingsLocked.classList.add("hidden");
    settingsManager.classList.remove("hidden");
    openDateEditorButton.textContent = getScheduleDayByDate(scheduleDateInput.value) ? "Open Editor" : "Create Date";
    showSettingsMessage("Settings unlocked.", "success");
  } catch (error) {
    showSettingsMessage(error.message || "Could not unlock settings.", "error");
  }
}

function getScheduleDayByDate(dateValue) {
  return scheduleConfig.find(function (day) {
    return day.date === dateValue;
  }) || null;
}

function getEditorDefaults() {
  const selectedDay = getScheduleDayByDate(scheduleDateInput.value);
  if (selectedDay) {
    return selectedDay;
  }
  if (scheduleConfig.length > 0) {
    return scheduleConfig[0];
  }
  return {
    panels: fallbackPanels,
    studentSlots: fallbackStudentSlots,
  };
}

function buildTimeSlotLabel(startTime, endTime) {
  return startTime + " - " + endTime;
}

function splitTimeSlotLabel(slotLabel) {
  const parts = String(slotLabel || "").split(" - ");
  return {
    start: parts[0] || "",
    end: parts[1] || "",
  };
}

function clearEditorList(listElement) {
  listElement.innerHTML = "";
}

function createFieldGroup(labelText, inputElement) {
  const wrapper = document.createElement("div");
  const label = document.createElement("span");
  label.className = "mini-label";
  label.textContent = labelText;
  wrapper.appendChild(label);
  wrapper.appendChild(inputElement);
  return wrapper;
}

function makeDraggableRow(row, listElement) {
  row.draggable = true;
  row.classList.add("draggable-row");

  row.addEventListener("dragstart", function (event) {
    dragState = { row: row, list: listElement };
    row.classList.add("dragging");
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", "dragging");
    }
  });

  row.addEventListener("dragend", function () {
    row.classList.remove("dragging");
    dragState = null;
  });
}

function createDragHandle(title) {
  const handle = document.createElement("button");
  handle.type = "button";
  handle.className = "drag-handle";
  handle.title = title;
  handle.textContent = "⋮⋮";
  handle.addEventListener("mousedown", function () {
    handle.closest(".draggable-row").setAttribute("draggable", "true");
  });
  return handle;
}

function createRemoveButton(row) {
  const removeButton = document.createElement("button");
  removeButton.type = "button";
  removeButton.className = "row-remove";
  removeButton.title = "Remove";
  removeButton.textContent = "✕";
  removeButton.addEventListener("click", function () {
    row.remove();
  });
  return removeButton;
}

function attachListDragBehavior(listElement) {
  listElement.addEventListener("dragover", function (event) {
    if (!dragState || dragState.list !== listElement) {
      return;
    }

    event.preventDefault();
    const afterElement = getDragAfterElement(listElement, event.clientY);
    if (afterElement == null) {
      listElement.appendChild(dragState.row);
    } else {
      listElement.insertBefore(dragState.row, afterElement);
    }
  });
}

function getDragAfterElement(listElement, yPosition) {
  const rows = Array.from(listElement.querySelectorAll(".draggable-row:not(.dragging)"));
  let closest = { offset: Number.NEGATIVE_INFINITY, element: null };

  rows.forEach(function (row) {
    const box = row.getBoundingClientRect();
    const offset = yPosition - box.top - box.height / 2;
    if (offset < 0 && offset > closest.offset) {
      closest = { offset: offset, element: row };
    }
  });

  return closest.element;
}

function addPanelEditorRow(value) {
  const row = document.createElement("div");
  row.className = "editor-row";
  makeDraggableRow(row, panelEditorList);

  const handle = createDragHandle("Drag to reorder panel");

  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = "Panel name";
  input.value = value || "";
  input.dataset.role = "panel-name";

  const actions = document.createElement("div");
  actions.className = "row-actions";
  actions.appendChild(createRemoveButton(row));

  row.appendChild(handle);
  row.appendChild(createFieldGroup("Panel", input));
  row.appendChild(actions);
  panelEditorList.appendChild(row);
}

function addSlotEditorRow(startTime, endTime) {
  const row = document.createElement("div");
  row.className = "time-row";
  makeDraggableRow(row, slotEditorList);

  const handle = createDragHandle("Drag to reorder time slot");

  const startInput = document.createElement("input");
  startInput.type = "time";
  startInput.value = startTime || "";
  startInput.dataset.role = "slot-start";

  const endInput = document.createElement("input");
  endInput.type = "time";
  endInput.value = endTime || "";
  endInput.dataset.role = "slot-end";

  const actions = document.createElement("div");
  actions.className = "row-actions";
  actions.appendChild(createRemoveButton(row));

  row.appendChild(handle);
  row.appendChild(createFieldGroup("From", startInput));
  row.appendChild(createFieldGroup("To", endInput));
  row.appendChild(actions);
  slotEditorList.appendChild(row);
}

function autofillHalfHourSlots() {
  clearEditorList(slotEditorList);

  let hour = 9;
  let minute = 0;

  while (hour < 18) {
    const startTime = String(hour).padStart(2, "0") + ":" + String(minute).padStart(2, "0");
    minute += 30;
    if (minute === 60) {
      hour += 1;
      minute = 0;
    }
    const endTime = String(hour).padStart(2, "0") + ":" + String(minute).padStart(2, "0");
    addSlotEditorRow(startTime, endTime);
  }
}

function sortPanelEditorRows() {
  const rows = Array.from(panelEditorList.querySelectorAll(".editor-row"));
  rows.sort(function (leftRow, rightRow) {
    const leftValue = leftRow.querySelector('input[data-role="panel-name"]').value.trim().toLowerCase();
    const rightValue = rightRow.querySelector('input[data-role="panel-name"]').value.trim().toLowerCase();
    return leftValue.localeCompare(rightValue);
  }).forEach(function (row) {
    panelEditorList.appendChild(row);
  });
}

function sortSlotEditorRows() {
  const rows = Array.from(slotEditorList.querySelectorAll(".time-row"));
  rows.sort(function (leftRow, rightRow) {
    const leftStart = leftRow.querySelector('input[data-role="slot-start"]').value;
    const rightStart = rightRow.querySelector('input[data-role="slot-start"]').value;
    const leftEnd = leftRow.querySelector('input[data-role="slot-end"]').value;
    const rightEnd = rightRow.querySelector('input[data-role="slot-end"]').value;
    return (leftStart + leftEnd).localeCompare(rightStart + rightEnd);
  }).forEach(function (row) {
    slotEditorList.appendChild(row);
  });
}

function populateDateEditor(dayConfig) {
  clearEditorList(panelEditorList);
  clearEditorList(slotEditorList);

  if (!dayConfig) {
    addPanelEditorRow("");
    addSlotEditorRow("", "");
    return;
  }

  dayConfig.panels.forEach(function (panelName) {
    addPanelEditorRow(panelName);
  });

  dayConfig.studentSlots.forEach(function (slotLabel) {
    const slot = splitTimeSlotLabel(slotLabel);
    addSlotEditorRow(slot.start, slot.end);
  });
}

function openDateEditor(dateValue) {
  if (!settingsPassword) {
    showSettingsMessage("Unlock settings first.", "error");
    return;
  }

  if (!dateValue) {
    showSettingsMessage("Choose a date first.", "error");
    scheduleDateInput.focus();
    return;
  }

  editingDateValue = dateValue;
  scheduleDateInput.value = dateValue;
  const dayConfig = getScheduleDayByDate(dateValue);
  dateEditorSubtitle.textContent = "Editing " + dateValue + ". Add panels individually and build time slots with from/to times.";
  populateDateEditor(dayConfig);
  showModalMessage("", "");
  dateEditorModal.classList.remove("hidden");
  dateEditorModal.setAttribute("aria-hidden", "false");
}

function closeDateEditor() {
  dateEditorModal.classList.add("hidden");
  dateEditorModal.setAttribute("aria-hidden", "true");
  showModalMessage("", "");
}

function collectPanelValues() {
  const seen = new Set();
  const values = [];

  panelEditorList.querySelectorAll('input[data-role="panel-name"]').forEach(function (input) {
    const value = input.value.trim();
    const key = value.toLowerCase();
    if (!value || seen.has(key)) {
      return;
    }
    seen.add(key);
    values.push(value);
  });

  return values;
}

function collectSlotValues() {
  const values = [];
  const seen = new Set();
  const rows = slotEditorList.querySelectorAll(".time-row");

  for (const row of rows) {
    const startInput = row.querySelector('input[data-role="slot-start"]');
    const endInput = row.querySelector('input[data-role="slot-end"]');
    const startTime = startInput.value;
    const endTime = endInput.value;

    if (!startTime && !endTime) {
      continue;
    }
    if (!startTime || !endTime) {
      throw new Error("Complete both times for every slot.");
    }
    if (startTime >= endTime) {
      throw new Error("Each slot must end after it starts.");
    }

    const label = buildTimeSlotLabel(startTime, endTime);
    if (seen.has(label)) {
      continue;
    }

    seen.add(label);
    values.push(label);
  }

  return values;
}

async function saveDateConfiguration(dateValue, panels, studentSlots) {
  if (!settingsPassword) {
    throw new Error("Unlock settings first.");
  }

  await apiFetch("/schedule/dates/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
      body: JSON.stringify({
        password: settingsPassword,
        bookingType: bookingType,
        date: dateValue,
        panels: panels,
        studentSlots: studentSlots,
    }),
  });
}

async function saveDateConfigurationFromModal() {
  saveDateConfigButton.disabled = true;
  saveDateConfigButton.textContent = "Saving...";
  try {
    const panels = collectPanelValues();
    const studentSlots = collectSlotValues();

    if (panels.length === 0) {
      throw new Error("Add at least one panel.");
    }
    if (studentSlots.length === 0) {
      throw new Error("Add at least one time slot.");
    }

    await saveDateConfiguration(editingDateValue, panels, studentSlots);

    await refreshData();
    hydrateBookingUi();
    renderSchedule();
    renderConfiguredDates();
    showModalMessage("Date configuration saved.", "success");
    showSettingsMessage("Date configuration saved.", "success");
    showToast("Date configuration saved.", "success");
    closeDateEditor();
  } catch (error) {
    const message = error.message || "Could not save date configuration.";
    showModalMessage(message, "error");
    showSettingsMessage(message, "error");
    showToast(message, "error");
  } finally {
    saveDateConfigButton.disabled = false;
    saveDateConfigButton.textContent = "Save Date Configuration";
  }
}

async function removeScheduleDate(dateValue) {
  if (!settingsPassword) {
    showSettingsMessage("Unlock settings first.", "error");
    return;
  }

  try {
    await apiFetch("/schedule/dates/", {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        password: settingsPassword,
        bookingType: bookingType,
        date: dateValue,
      }),
    });

    await refreshData();
    hydrateBookingUi();
    renderSchedule();
    renderConfiguredDates();
    showSettingsMessage("Date removed.", "success");
    showToast("Date removed.", "success");
  } catch (error) {
    const message = error.message || "Could not remove date.";
    showSettingsMessage(message, "error");
    showToast(message, "error");
  }
}

async function cancelActiveBooking(bookingId) {
  if (!settingsPassword) {
    showSettingsMessage("Unlock settings first.", "error");
    return;
  }

  try {
    await apiFetch("/bookings/" + bookingId + "/admin-cancel/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        password: settingsPassword,
        reason: "Cancelled from settings.",
      }),
    });

    await refreshData();
    hydrateBookingUi();
    renderSchedule();
    renderConfiguredDates();
    showSettingsMessage("Booking cancelled.", "success");
    showToast("Booking cancelled.", "success");
  } catch (error) {
    const message = error.message || "Could not cancel booking.";
    showSettingsMessage(message, "error");
    showToast(message, "error");
  }
}

function renderConfiguredDates() {
  settingsDatesList.innerHTML = "";
  activeBookingsList.innerHTML = "";

  if (scheduleConfig.length === 0) {
    const empty = document.createElement("div");
    empty.className = "date-row";
    empty.innerHTML = "<strong>No dates configured yet.</strong>";
    settingsDatesList.appendChild(empty);
    return;
  }

  scheduleConfig.forEach(function (day) {
    const row = document.createElement("div");
    row.className = "date-row";

    const label = document.createElement("strong");
    label.textContent = day.displayDate;

    const actions = document.createElement("div");
    actions.className = "date-row-actions";

    const editButton = document.createElement("button");
    editButton.type = "button";
    editButton.textContent = "Edit";
    editButton.title = "Edit date settings";
    editButton.className = "secondary icon-button";
    editButton.addEventListener("click", function () {
      openDateEditor(day.date);
    });

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.textContent = "Remove";
    removeButton.className = "danger";
    removeButton.addEventListener("click", function () {
      removeScheduleDate(day.date);
    });

    row.appendChild(label);
    actions.appendChild(editButton);
    actions.appendChild(removeButton);
    row.appendChild(actions);
    settingsDatesList.appendChild(row);
  });

  if (bookings.length === 0) {
    const emptyBookings = document.createElement("div");
    emptyBookings.className = "date-row";
    emptyBookings.innerHTML = "<strong>No active bookings.</strong>";
    activeBookingsList.appendChild(emptyBookings);
    return;
  }

  bookings.forEach(function (booking) {
    const row = document.createElement("div");
    row.className = "date-row booking-row";

    const details = document.createElement("div");
    details.className = "booking-meta";
    details.innerHTML =
      "<strong>" + booking.name + "</strong>" +
      "<span>" + booking.dateDisplay + " • " + booking.panel + " • " + booking.slot + "</span>" +
      "<span>" + booking.email + "</span>";

    const cancelButton = document.createElement("button");
    cancelButton.type = "button";
    cancelButton.textContent = "Cancel";
    cancelButton.className = "danger";
    cancelButton.addEventListener("click", function () {
      cancelActiveBooking(booking.id);
    });

    row.appendChild(details);
    row.appendChild(cancelButton);
    activeBookingsList.appendChild(row);
  });
}

function showMessage(text, type) {
  messageBox.textContent = text;
  messageBox.className = "message " + type;
}

function showSettingsMessage(text, type) {
  settingsMessageBox.textContent = text;
  settingsMessageBox.className = "message " + type;
}

function showModalMessage(text, type) {
  if (!text) {
    dateEditorMessage.textContent = "";
    dateEditorMessage.className = "message modal-message";
    return;
  }

  dateEditorMessage.textContent = text;
  dateEditorMessage.className = "message modal-message " + type;
}

function showToast(text, type) {
  const toast = document.createElement("div");
  toast.className = "toast " + (type || "success");
  toast.textContent = text;
  toastStack.appendChild(toast);

  setTimeout(function () {
    toast.remove();
  }, 3600);
}

window.bookSlot = bookSlot;

document.addEventListener("DOMContentLoaded", startApp);
attachListDragBehavior(panelEditorList);
attachListDragBehavior(slotEditorList);
