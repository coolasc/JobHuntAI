"""Job scraping from public job-board APIs plus CV matching."""
import re
import urllib.parse

from .providers import _request

STOP = set("""a an and are as at be by for from has have in is it its of on or that the to was were will with
you your our we i my me this these those their they them not but can do does did over per via into such than then""".split())


def tokens(text):
    return {w for w in re.findall(r"[a-z][a-z+#.\-]{1,}", text.lower()) if w not in STOP and len(w) > 2}


def strip_html(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def score(cv_tokens, job):
    jt = tokens(job["title"] + " " + job["description"])
    if not jt:
        return 0.0
    return round(100 * len(cv_tokens & jt) / len(jt), 1)


def search_remotive(query):
    r = _request("https://remotive.com/api/remote-jobs?" + urllib.parse.urlencode({"search": query, "limit": 50}), timeout=20)
    return [{"title": j["title"], "company": j["company_name"], "location": j.get("candidate_required_location", "Remote"),
             "work_mode": "remote", "url": j["url"], "description": strip_html(j.get("description"))}
            for j in r.get("jobs", [])]


def search_arbeitnow(query):
    r = _request("https://www.arbeitnow.com/api/job-board-api", timeout=20)
    q = tokens(query)
    out = []
    for j in r.get("data", []):
        text = j["title"] + " " + j.get("description", "")
        if q and not q & tokens(text):
            continue
        out.append({"title": j["title"], "company": j["company_name"], "location": j.get("location", ""),
                    "work_mode": "remote" if j.get("remote") else "in-person", "url": j["url"],
                    "description": strip_html(j.get("description"))})
    return out


SOURCES = [search_remotive, search_arbeitnow]


def top_keywords(cv_text, n=6):
    freq = {}
    for w in re.findall(r"[a-z][a-z+#.\-]{2,}", cv_text.lower()):
        if w not in STOP:
            freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda kv: -kv[1])[:n]]


def filter_jobs(jobs, location, mode):
    loc = location.strip().lower()
    out = []
    for j in jobs:
        if mode == "remote" and j["work_mode"] != "remote":
            continue
        if mode in ("in-person", "hybrid") and loc and loc not in j["location"].lower():
            continue
        if mode == "in-person" and j["work_mode"] == "remote":
            continue
        out.append(j)
    return out


def find_jobs(cv_text, location, mode, limit=10, sources=None):
    cv_tokens = tokens(cv_text)
    jobs, seen = [], set()
    for kw in top_keywords(cv_text, 3):
        for src in (sources or SOURCES):
            try:
                found = src(kw)
            except Exception:
                continue
            for j in found:
                if j["url"] not in seen:
                    seen.add(j["url"])
                    jobs.append(j)
    jobs = filter_jobs(jobs, location, mode)
    for j in jobs:
        j["score"] = score(cv_tokens, j)
    jobs.sort(key=lambda j: -j["score"])
    return jobs[:limit]
