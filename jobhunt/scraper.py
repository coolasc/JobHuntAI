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


# country -> (ISO code, place names used to recognise that country in a job's location text)
COUNTRIES = {
    "ireland": ("IE", ["ireland", "dublin", "cork", "galway", "limerick", "waterford", "belfast", "ie"]),
    "united kingdom": ("GB", ["united kingdom", "uk", "england", "scotland", "wales", "london", "manchester", "edinburgh"]),
    "united states": ("US", ["united states", "usa", "us", "new york", "san francisco", "seattle", "austin", "california"]),
    "germany": ("DE", ["germany", "deutschland", "berlin", "munich", "hamburg", "frankfurt"]),
    "france": ("FR", ["france", "paris", "lyon"]),
    "netherlands": ("NL", ["netherlands", "amsterdam", "rotterdam", "utrecht"]),
    "spain": ("ES", ["spain", "madrid", "barcelona"]),
    "canada": ("CA", ["canada", "toronto", "vancouver", "montreal"]),
    "india": ("IN", ["india", "bangalore", "bengaluru", "hyderabad", "mumbai"]),
    "australia": ("AU", ["australia", "sydney", "melbourne"]),
}


def resolve_country(location):
    """Return the canonical country name for a free-text location such as 'Dublin' or 'Ireland', else None."""
    words = set(re.findall(r"[a-z]+", (location or "").lower()))
    text = " " + " ".join(re.findall(r"[a-z]+", (location or "").lower())) + " "
    for name, (code, places) in COUNTRIES.items():
        if f" {name} " in text or any((" " + p + " ") in text if " " in p else p in words for p in places):
            return name
    return None


def in_country(job_location, country):
    if not country:
        return True
    text = " " + " ".join(re.findall(r"[a-z]+", (job_location or "").lower())) + " "
    return any(f" {p} " in text for p in COUNTRIES[country][1])


def _country_aware(fn):
    fn.country_aware = True
    return fn


@_country_aware
def search_themuse(query, country=None):
    params = {"page": 0}
    if country:
        params["location"] = country.title()
    r = _request("https://www.themuse.com/api/public/jobs?" + urllib.parse.urlencode(params), timeout=20)
    q = tokens(query)
    out = []
    for j in r.get("results", []):
        locs = ", ".join(l.get("name", "") for l in j.get("locations", [])) or "Flexible / Remote"
        text = j.get("name", "") + " " + strip_html(j.get("contents"))
        if q and not q & tokens(text):
            continue
        out.append({"title": j["name"], "company": j.get("company", {}).get("name", ""), "location": locs,
                    "work_mode": "remote" if "remote" in locs.lower() or "flexible" in locs.lower() else "in-person",
                    "url": j["refs"]["landing_page"], "description": strip_html(j.get("contents"))})
    return out


@_country_aware
def search_jobicy(query, country=None):
    params = {"count": 50, "tag": query}
    if country:
        params["geo"] = country.replace(" ", "-")
    r = _request("https://jobicy.com/api/v2/remote-jobs?" + urllib.parse.urlencode(params), timeout=20)
    return [{"title": j["jobTitle"], "company": j.get("companyName", ""), "location": j.get("jobGeo", "Remote"),
             "work_mode": "remote", "url": j["url"], "description": strip_html(j.get("jobDescription"))}
            for j in r.get("jobs", [])]


@_country_aware
def search_microsoft(query, country=None):
    """Microsoft Careers (careers.microsoft.com) public search API."""
    params = {"q": query, "l": "en_us", "pg": 1, "pgSz": 20, "o": "Relevance"}
    if country:
        params["lc"] = country.title()
    r = _request("https://gcsservices.careers.microsoft.com/search/api/v1/search?" + urllib.parse.urlencode(params), timeout=20)
    out = []
    for j in (r.get("operationResult", {}).get("result", {}) or {}).get("jobs", []):
        props = j.get("properties", {})
        locs = props.get("locations") or [props.get("primaryLocation", "")]
        out.append({"title": j["title"], "company": "Microsoft", "location": ", ".join(locs),
                    "work_mode": "remote" if str(props.get("workSiteFlexibility", "")).lower().startswith("100") else "in-person",
                    "url": "https://jobs.careers.microsoft.com/global/en/job/" + str(j["jobId"]),
                    "description": strip_html(j.get("description") or props.get("description", ""))})
    return out


@_country_aware
def search_google(query, country=None):
    """Google Careers (careers.google.com) public search API."""
    params = {"q": query, "page_size": 20}
    if country:
        params["location"] = country.title()
    r = _request("https://careers.google.com/api/v3/search/?" + urllib.parse.urlencode(params), timeout=20)
    return [{"title": j["title"], "company": "Google", "location": "; ".join(l.get("display", "") for l in j.get("locations", [])),
             "work_mode": "remote" if j.get("has_remote") else "in-person", "url": j.get("apply_url", ""),
             "description": strip_html(j.get("description", "") + " " + j.get("summary", ""))}
            for j in r.get("jobs", []) if j.get("apply_url")]


# Companies that publish openings through public Greenhouse boards (boards-api.greenhouse.io)
GREENHOUSE_COMPANIES = {"stripe": "Stripe", "airbnb": "Airbnb", "datadog": "Datadog", "intercom": "Intercom",
                        "cloudflare": "Cloudflare", "twilio": "Twilio", "dropbox": "Dropbox"}


@_country_aware
def search_greenhouse(query, country=None):
    q = tokens(query)
    out = []
    for slug, name in GREENHOUSE_COMPANIES.items():
        try:
            r = _request(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true", timeout=20)
        except Exception:
            continue
        for j in r.get("jobs", []):
            loc = (j.get("location") or {}).get("name", "")
            if not in_country(loc, country):
                continue
            desc = strip_html(j.get("content"))
            if q and not q & tokens(j["title"] + " " + desc):
                continue
            out.append({"title": j["title"], "company": name, "location": loc,
                        "work_mode": "remote" if "remote" in loc.lower() else "in-person",
                        "url": j["absolute_url"], "description": desc})
    return out


SOURCES = [search_remotive, search_arbeitnow, search_themuse, search_jobicy,
           search_microsoft, search_google, search_greenhouse]


def top_keywords(cv_text, n=6):
    freq = {}
    for w in re.findall(r"[a-z][a-z+#.\-]{2,}", cv_text.lower()):
        if w not in STOP:
            freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda kv: -kv[1])[:n]]


def filter_jobs(jobs, location, mode):
    loc = location.strip().lower()
    country = resolve_country(location)
    out = []
    for j in jobs:
        if country and mode != "remote" and not in_country(j["location"], country):
            continue
        if mode == "remote" and j["work_mode"] != "remote":
            continue
        if mode in ("in-person", "hybrid") and loc and not country and loc not in j["location"].lower():
            continue
        if mode == "in-person" and j["work_mode"] == "remote":
            continue
        out.append(j)
    return out


def find_jobs(cv_text, location, mode, limit=10, sources=None):
    cv_tokens = tokens(cv_text)
    country = resolve_country(location)
    jobs, seen = [], set()
    for kw in top_keywords(cv_text, 3):
        for src in (sources or SOURCES):
            try:
                found = src(kw, country) if getattr(src, "country_aware", False) else src(kw)
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
