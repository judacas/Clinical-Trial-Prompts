"""
This just allows me to use quickly use a log to see how much I could parallelize the processing of the trials without going over the rate limit
not really meant for production, just a quick check, will be incorporated much better eventually. Used this to find out that about 100 workers is the perfect number to get around 75% use of rate limits
"""

import re

log_file_path = "../../logs/clinical_trial_analysis_20250312_050821.log"


def extract_cycles(field_prefix, encoding="latin-1"):
    """
    Extract cycles for a given field_prefix (e.g. "tokens" or "requests").
    Each cycle is determined by consecutive log lines where the reset value
    decreases or stays the same. When it increases, we consider the previous cycle complete.

    Returns a list of dictionaries with keys: timestamp, limit, remaining, reset, used, percent_used.
    """
    # Compile regex patterns dynamically.
    timestamp_pat = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
    limit_pat = re.compile(r"b'x-ratelimit-limit-" + field_prefix + r"', b'(\d+)'")
    remaining_pat = re.compile(
        r"b'x-ratelimit-remaining-" + field_prefix + r"', b'(\d+)'"
    )
    reset_pat = re.compile(r"b'x-ratelimit-reset-" + field_prefix + r"', b'(\d+)ms'")

    records = []
    with open(log_file_path, "r", encoding=encoding) as f:
        for line in f:
            if "x-ratelimit-reset-" + field_prefix in line:
                ts_match = timestamp_pat.search(line)
                ts = ts_match.group(1) if ts_match else None
                limit_match = limit_pat.search(line)
                remaining_match = remaining_pat.search(line)
                reset_match = reset_pat.search(line)
                if limit_match and remaining_match and reset_match:
                    record = {
                        "timestamp": ts,
                        "limit": int(limit_match.group(1)),
                        "remaining": int(remaining_match.group(1)),
                        "reset": int(reset_match.group(1)),
                    }
                    records.append(record)

    # Group records into cycles.
    cycles = []
    if records:
        current_cycle = [records[0]]
        for rec in records[1:]:
            # Within a cycle, the reset value should decrease (or remain the same).
            # A jump up indicates the start of a new cycle.
            if rec["reset"] <= current_cycle[-1]["reset"]:
                current_cycle.append(rec)
            else:
                cycles.append(current_cycle[-1])
                current_cycle = [rec]
        if current_cycle:
            cycles.append(current_cycle[-1])

    # Calculate used and percent used for each cycle.
    results = []
    for cycle in cycles:
        used = cycle["limit"] - cycle["remaining"]
        percent_used = (used / cycle["limit"]) * 100 if cycle["limit"] else 0
        results.append(
            {
                "timestamp": cycle["timestamp"],
                "reset": cycle["reset"],
                "remaining": cycle["remaining"],
                "used": used,
                "percent_used": percent_used,
            }
        )
    return results


# Extract cycles for tokens and requests.
token_cycles = extract_cycles("tokens")
request_cycles = extract_cycles("requests")


# Function to compute averages.
def compute_averages(cycles, field_name):
    if not cycles:
        return f"No {field_name} data found."

    total_used = sum(cycle["used"] for cycle in cycles)
    total_percent = sum(cycle["percent_used"] for cycle in cycles)
    avg_used = total_used / len(cycles) if cycles else 0
    avg_percent = total_percent / len(cycles) if cycles else 0

    return {
        "field": field_name,
        "average_used": avg_used,
        "average_percent_used": avg_percent,
        "total_cycles": len(cycles),
    }


# Compute averages
token_stats = compute_averages(token_cycles, "tokens")
request_stats = compute_averages(request_cycles, "requests")

print(token_stats)

print(request_stats)
