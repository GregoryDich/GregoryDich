"""
gdelt_client.py — Live narrative-intensity timelines from GDELT DOC 2.0.

WIRED AND READY. In this sandbox the host api.gdeltproject.org is not on the
network egress allowlist, so live calls return 403. To enable real data:
  1. Add `api.gdeltproject.org` to the environment's network egress settings
     (see https://code.claude.com/docs/en/claude-code-on-the-web).
  2. Run:  python build_poc.py --source gdelt

GDELT `timelinevol` returns the share of global news volume matching a query,
in 15-minute / daily increments -> our narrative-intensity series.
"""
import requests

API = "https://api.gdeltproject.org/api/v2/doc/doc"
UA = {"User-Agent": "Mozilla/5.0 (narrative-economics research PoC)"}

# Default competing-narrative queries (tune as needed).
QUERY_DESTRUCTION = '("AI will take" OR "AI replacing" OR "replaced by AI" OR "AI job losses") (jobs OR work OR layoffs)'
QUERY_CREATION = '("AI side hustle" OR "build with AI" OR "AI lets anyone" OR "vibe coding" OR "AI opportunity") (jobs OR work OR business)'


def fetch_timeline(query, timespan="5y", timeout=30):
    """Return (dates, intensity) for a query. Raises on network/HTTP error."""
    params = {"query": query, "mode": "timelinevol",
              "format": "json", "timespan": timespan}
    r = requests.get(API, params=params, headers=UA, timeout=timeout)
    r.raise_for_status()
    series = r.json()["timeline"][0]["data"]
    dates = [pt["date"] for pt in series]
    intensity = [float(pt["value"]) for pt in series]
    return dates, intensity


def fetch_competing(timespan="5y"):
    """Fetch both narratives. Returns dict with 'minus' and 'plus' timelines."""
    dm, im = fetch_timeline(QUERY_DESTRUCTION, timespan)
    dp, ip = fetch_timeline(QUERY_CREATION, timespan)
    return {"minus": (dm, im), "plus": (dp, ip)}
