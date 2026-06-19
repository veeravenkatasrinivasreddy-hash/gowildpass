"""
Flask backend for GoWild Pass flight finder.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request, jsonify
from flask import send_from_directory
from airports import get_nearby
from frontier import search_flights, book_flight

FRONTEND = os.path.join(os.path.dirname(__file__), '..', 'frontend')
app = Flask(__name__, static_folder=FRONTEND, static_url_path="")


@app.route("/")
def index():
    return send_from_directory(FRONTEND, "index.html")


@app.route("/api/search", methods=["POST"])
def search():
    data = request.json
    origin = data.get("origin", "").upper()
    destination = data.get("destination", "").upper()
    date = data.get("date", "")

    if not origin or not destination or not date:
        return jsonify({"error": "origin, destination, and date are required"}), 400

    nearby = data.get("nearby", False)
    origins = get_nearby(origin) if nearby else [origin]
    destinations = get_nearby(destination) if nearby else [destination]

    all_flights = []
    for org in origins:
        for dst in destinations:
            flights = search_flights(org, dst, date)
            for f in flights:
                f["origin"] = org
                f["destination"] = dst
            all_flights.extend(flights)

    return jsonify({
        "flights": all_flights,
        "searched_origins": origins,
        "searched_destinations": destinations,
    })


@app.route("/api/book", methods=["POST"])
def book():
    data = request.json
    origin = data.get("origin", "").upper()
    destination = data.get("destination", "").upper()
    date = data.get("date", "")
    flight_index = data.get("flight_index", 0)

    if not origin or not destination or not date:
        return jsonify({"error": "origin, destination, and date are required"}), 400

    result = book_flight(origin, destination, date, flight_index)
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
