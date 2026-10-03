"""CSV log of every job found: when, where, and whether it is remote/hybrid/local."""
import csv
from datetime import datetime

from . import scraper, settings

FIELDS = ["found_at", "title", "company", "country", "work_mode", "location", "url", "score"]


def csv_path():
    return settings.settings_path().parent / "jobs.csv"


def _mode(job, search_mode):
    if job.get("work_mode") == "remote":
        return "remote"
    return "hybrid" if search_mode == "hybrid" else "local"


def _safe(v):
    v = str(v if v is not None else "")
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


def record(jobs, search_mode, search_location=""):
    """Append jobs not yet in the CSV (matched by URL). Returns number added."""
    p = csv_path()
    known = set()
    if p.exists():
        with p.open(newline="", encoding="utf-8") as f:
            known = {r.get("url") for r in csv.DictReader(f)}
    new = [j for j in jobs if j.get("url") and _safe(j["url"]) not in known]
    if not new:
        return 0
    p.parent.mkdir(parents=True, exist_ok=True)
    fresh = not p.exists()
    now = datetime.now().isoformat(timespec="seconds")
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if fresh:
            w.writerow(FIELDS)
        for j in new:
            country = scraper.resolve_country(j.get("location", "")) or scraper.resolve_country(search_location) or ""
            w.writerow([_safe(x) for x in (now, j.get("title"), j.get("company"), country.title(),
                                           _mode(j, search_mode), j.get("location"), j["url"], j.get("score", ""))])
    return len(new)
