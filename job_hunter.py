import csv
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Remote-only feed from Remotive. All experience levels are included.
SEARCHES = {
    "web developer": ["web developer", "frontend developer", "backend developer", "full stack developer"],
    "app developer": ["app developer", "mobile developer", "android developer", "ios developer"],
    "IT support": ["IT support", "technical support", "help desk", "service desk"],
    "network support": ["network support", "network administrator", "network engineer"],
}
OUT = Path("output")
OUT.mkdir(exist_ok=True)

POSITIVE = re.compile(r"\b(web|frontend|front-end|backend|back-end|full[ -]?stack|software engineer|software developer|app developer|mobile developer|android|ios developer|it support|technical support|help ?desk|service desk|network support|network administrator|network engineer|systems administrator|desktop support|application support|developer|programmer)\b", re.I)
NEGATIVE = re.compile(r"\b(writer|writing|copywriter|content reviewer|content moderator|data scientist|sales|marketing|office assistant|recruiter|customer service representative|ai response evaluator)\b", re.I)


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "FreeITJobHunter/2.0 (personal job search)"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def linkedin_url(keyword, location, remote=False):
    params = {"keywords": keyword, "location": location}
    if remote:
        params["f_WT"] = "2"  # LinkedIn remote filter
    return "https://www.linkedin.com/jobs/search/?" + urllib.parse.urlencode(params)


def classify(title, category):
    text = f"{title} {category}"
    if re.search(r"network|systems administrator|network engineer", text, re.I):
        return "Network Support"
    if re.search(r"support|help ?desk|service desk|desktop", text, re.I):
        return "IT / Technical Support"
    if re.search(r"app developer|mobile developer|android|ios developer", text, re.I):
        return "App Developer"
    if re.search(r"web|frontend|front-end|backend|back-end|full[ -]?stack", text, re.I):
        return "Web Developer"
    return "Software / IT"


def location_fit(location):
    loc = (location or "").strip()
    low = loc.lower()
    if not loc:
        return "Check employer eligibility"
    if "worldwide" in low or "anywhere" in low or "global" in low:
        return "Remote worldwide (verify Pakistan eligibility)"
    if "pakistan" in low:
        return "Remote; Pakistan explicitly listed"
    if any(x in low for x in ["usa", "united states", "canada", "uk", "united kingdom", "europe"]):
        if not any(x in low for x in ["worldwide", "pakistan", "global"]):
            return "May be location-restricted; verify before applying"
    return "Remote; verify Pakistan eligibility"


def main():
    seen = set()
    jobs = []
    errors = []
    for group, keywords in SEARCHES.items():
        for keyword in keywords:
            url = "https://remotive.com/api/remote-jobs?" + urllib.parse.urlencode({"search": keyword})
            try:
                payload = fetch_json(url)
                for item in payload.get("jobs", []):
                    job_url = (item.get("url") or "").strip()
                    title = (item.get("title") or "").strip()
                    category = (item.get("category") or "").strip()
                    if not job_url or job_url in seen:
                        continue
                    searchable = f"{title} {category} {item.get('description', '')}"
                    if not POSITIVE.search(searchable) or NEGATIVE.search(title):
                        continue
                    seen.add(job_url)
                    loc = item.get("candidate_required_location", "")
                    jobs.append({
                        "collected_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                        "matched_search": keyword,
                        "job_family": classify(title, category),
                        "title": title,
                        "company": item.get("company_name", ""),
                        "category": category,
                        "job_type": item.get("job_type", ""),
                        "publication_date": item.get("publication_date", ""),
                        "candidate_location": loc,
                        "Pakistan_eligibility": location_fit(loc),
                        "url": job_url,
                        "source": "Remotive public API (remote roles)",
                        "LinkedIn_remote_search": linkedin_url(keyword, "Pakistan", True),
                        "LinkedIn_Karachi_onsite_search": linkedin_url(keyword, "Karachi, Sindh, Pakistan", False),
                        "experience_level": "All levels — verify job requirements",
                        "application_status": "Not applied",
                    })
            except Exception as exc:
                errors.append(f"{keyword}: {exc}")

    jobs.sort(key=lambda row: row.get("publication_date", ""), reverse=True)
    fields = ["collected_utc", "matched_search", "job_family", "title", "company", "category", "job_type", "publication_date", "candidate_location", "Pakistan_eligibility", "url", "source", "LinkedIn_remote_search", "LinkedIn_Karachi_onsite_search", "experience_level", "application_status"]
    with (OUT / "jobs.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(jobs)

    (OUT / "summary.txt").write_text("\n".join([
        f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Relevant remote jobs collected: {len(jobs)}",
        "Target roles: Web/App Developer, IT Support, Technical Support, Network Support.",
        "Experience: all levels are searched; confirm requirements on each listing.",
        "Location preference: international roles only when remote and Pakistan-eligible; Pakistan onsite roles should be Karachi only. This Remotive feed contains remote jobs only; it does not collect onsite jobs.",
        "Each row includes LinkedIn searches for remote roles in Pakistan and onsite roles in Karachi.",
        "LinkedIn is not scraped. Applications, messages, and comments are not submitted automatically.",
        "Check the employer's official listing before applying; location labels can be ambiguous."
    ] + (["", "Some searches failed:"] + errors if errors else [])), encoding="utf-8")
    (OUT / "recruiter_comment_drafts.txt").write_text("""RECRUITER COMMENT DRAFTS — review and personalize before posting

1. Thank you for sharing this opportunity. I’m exploring Web/App Development and IT Support roles and would appreciate any guidance on the application process.

2. Thanks for posting this opening. I’ll review the requirements and apply through the official channel if my skills and location eligibility match.

3. Appreciate you sharing this role. Is this position open to applicants based in Pakistan for remote work?

Reminder: personalize comments and post manually. This tool does not interact with LinkedIn.
""", encoding="utf-8")
    print(f"Relevant remote jobs collected: {len(jobs)}")
    if errors:
        print(f"Search errors: {len(errors)}; see output/summary.txt")

if __name__ == "__main__":
    main()
