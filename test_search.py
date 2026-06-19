import sys
sys.path.insert(0, "backend")
from frontier import search_flights

print("Starting search...")
results = search_flights("CVG", "ATL", "2026-06-25")
print("Results found:", len(results))
for r in results:
    print(r)
