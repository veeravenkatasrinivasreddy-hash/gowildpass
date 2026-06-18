"""
Nearby Frontier airports lookup.
Returns airports within ~250 miles of a given city code.
"""

NEARBY = {
    "CVG": ["CVG", "DAY", "CMH", "IND", "LEX"],  # Cincinnati area
    "ATL": ["ATL", "BHM", "CHA", "AGS"],           # Atlanta area
    "ORD": ["ORD", "MDW", "MKE", "RFD"],           # Chicago area
    "DFW": ["DFW", "DAL", "AUS", "SAT"],           # Dallas area
    "DEN": ["DEN", "COS", "PUB"],                  # Denver area
    "LAS": ["LAS", "ONT", "BUR", "LAX", "SNA"],   # Las Vegas area
    "LAX": ["LAX", "BUR", "LGB", "ONT", "SNA"],   # LA area
    "MIA": ["MIA", "FLL", "PBI", "MCO"],           # Miami area
    "MCO": ["MCO", "TPA", "PIE", "SFB"],           # Orlando area
    "PHX": ["PHX", "TUS", "YUM"],                  # Phoenix area
    "SEA": ["SEA", "BFI", "PAE"],                  # Seattle area
    "SFO": ["SFO", "OAK", "SJC"],                  # San Francisco area
    "JFK": ["JFK", "LGA", "EWR"],                  # New York area
    "BOS": ["BOS", "MHT", "PVD"],                  # Boston area
    "IAH": ["IAH", "HOU", "AUS"],                  # Houston area
}

# Reverse lookup: map every airport to its group
_REVERSE = {}
for primary, group in NEARBY.items():
    for code in group:
        if code not in _REVERSE:
            _REVERSE[code] = group


def get_nearby(airport_code: str) -> list[str]:
    """Return list of nearby airport codes including the given one."""
    code = airport_code.upper().strip()
    return _REVERSE.get(code, [code])
