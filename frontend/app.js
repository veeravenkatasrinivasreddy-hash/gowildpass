let pendingBooking = null;

// Show/hide return date based on trip type
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll('input[name="tripType"]').forEach(radio => {
    radio.addEventListener("change", () => {
      document.getElementById("return-field").style.display =
        radio.value === "RT" ? "block" : "none";
    });
  });
});

async function searchFlights() {
  const origin = document.getElementById("origin").value.trim().toUpperCase();
  const destination = document.getElementById("destination").value.trim().toUpperCase();
  const date = document.getElementById("date").value;

  if (!origin || !destination || !date) {
    showStatus("Please fill in all fields.", true);
    return;
  }

  const btn = document.getElementById("searchBtn");
  btn.disabled = true;
  btn.textContent = "Searching...";
  showStatus("Opening Frontier website and searching for GoWild flights...");
  hide("results");
  hide("airport-info");

  try {
    const res = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ origin, destination, date, trip_type: document.querySelector('input[name="tripType"]:checked').value, nearby: document.getElementById("nearbyAirports").checked }),
    });

    const data = await res.json();

    if (data.error) {
      showStatus(data.error, true);
      return;
    }

    // Show which airports were searched
    const airportInfo = document.getElementById("airport-info");
    document.getElementById("airport-text").textContent =
      `Searched: ${data.searched_origins.join(", ")} → ${data.searched_destinations.join(", ")}`;
    airportInfo.classList.remove("hidden");

    renderFlights(data.flights);
    hide("status");
  } catch (err) {
    showStatus("Could not connect to the server. Is the backend running?", true);
  } finally {
    btn.disabled = false;
    btn.textContent = "Search Flights";
  }
}

function renderFlights(flights) {
  const section = document.getElementById("results");
  const list = document.getElementById("flight-list");
  section.classList.remove("hidden");

  if (!flights || flights.length === 0) {
    list.innerHTML = `<div class="no-flights">No GoWild flights found. Try a different date or nearby airports.</div>`;
    return;
  }

  // Date price calendar (from first flight's date_prices)
  const datePrices = flights[0]?.date_prices || [];
  let calendarHtml = "";
  if (datePrices.length > 0) {
    calendarHtml = `
      <div class="date-calendar">
        <h3>GoWild Prices — Next 15 Days</h3>
        <div class="date-grid">
          ${datePrices.map(d => `
            <div class="date-cell ${d.price === '$16' ? 'price-low' : ''}">
              <div class="date-label">${d.date}</div>
              <div class="date-price">${d.price}</div>
            </div>
          `).join("")}
        </div>
      </div>`;
  }

  const searchDate = document.getElementById("date").value;
  const displayDate = searchDate ? new Date(searchDate + "T00:00:00").toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" }) : "";

  // Individual flights
  const flightCards = flights.filter(f => f.departure).map((f, i) => `
    <div class="flight-card">
      <div class="flight-info">
        <div class="flight-route">${f.origin} → ${f.destination}</div>
        <div class="flight-date">${displayDate}</div>
        <div class="flight-times">${f.departure} → ${f.arrival}</div>
        <div class="flight-meta">${f.duration} &nbsp;|&nbsp; ${f.stops}</div>
      </div>
      <div class="flight-price">${f.price}</div>
      <button class="btn-book" onclick="openBookModal(${f.index}, '${f.origin}', '${f.destination}')">
        Book
      </button>
    </div>
  `).join("");

  list.innerHTML = calendarHtml + (flightCards || `<div class="no-flights">No available flights on this date. Pick a date from the calendar above.</div>`);
}

function openBookModal(index, origin, destination) {
  const date = document.getElementById("date").value;
  pendingBooking = { index, origin, destination, date };

  document.getElementById("confirm-text").textContent =
    `Book a GoWild Pass flight from ${origin} to ${destination} on ${date} for $16?`;

  document.getElementById("confirm-modal").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("confirm-modal").classList.add("hidden");
  pendingBooking = null;
}

async function confirmBook() {
  if (!pendingBooking) return;
  closeModal();

  showStatus("Opening Frontier to complete your booking...");

  try {
    const res = await fetch("/api/book", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        origin: pendingBooking.origin,
        destination: pendingBooking.destination,
        date: pendingBooking.date,
        flight_index: pendingBooking.index,
      }),
    });

    const data = await res.json();

    if (data.success) {
      showStatus(`Booking confirmed! ${data.confirmation ? "Confirmation: " + data.confirmation : ""}`);
    } else {
      showStatus(`Booking failed: ${data.message}`, true);
    }
  } catch (err) {
    showStatus("Could not connect to the server.", true);
  }
}

function showStatus(msg, isError = false) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = "status" + (isError ? " error" : "");
  el.classList.remove("hidden");
}

function hide(id) {
  document.getElementById(id).classList.add("hidden");
}
