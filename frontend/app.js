let pendingBooking = null;

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
      body: JSON.stringify({ origin, destination, date }),
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
    list.innerHTML = `<div class="no-flights">No $16 GoWild flights found for this route and date.<br>Try nearby airports or a different date.</div>`;
    return;
  }

  list.innerHTML = flights.map((f, i) => `
    <div class="flight-card">
      <div>
        <div class="flight-route">${f.origin} → ${f.destination}</div>
        <div class="flight-meta">${f.raw || "GoWild Pass flight"}</div>
      </div>
      <div class="flight-price">${f.price}</div>
      <button class="btn-book" onclick="openBookModal(${i}, '${f.origin}', '${f.destination}')">
        Book
      </button>
    </div>
  `).join("");
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
