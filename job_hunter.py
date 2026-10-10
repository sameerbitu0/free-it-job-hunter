import csv
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Free starter: searches Remotive's public remote-jobs API.
# It does NOT scrape LinkedIn or submit applications/comments.
KEYWORDS = [
    "web developer",
    "frontend developer",
    "backend developer",
    "full stack developer",
    "app developer",
    "android developer",
    "software developer",
    "IT support",
    "technical support",
    "help desk",
    "network support",
    "network administrator",
    "IT officer",
]
OUT = Path("output")
OUT.mkdir(exist_ok=True)

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "FreeITJobHunter/1.0 (personal job search)"}
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

def linkedin_search_url(keyword):
    params = urllib.parse.urlencode({"keywords": keyword, "location": "Pakistan"})
    return "https://www.linkedin.com/jobs/search/?" + params

def main():
    seen = set()
    jobs = []
    errors = []

    for keyword in KEYWORDS:
        url = "https://remotive.com/api/remote-jobs?" + urllib.parse.urlencode({"search": keyword})
        try:
            payload = fetch_json(url)
            for item in payload.get("jobs", []):
                job_url = item.get("url", "").strip()
                if not job_url or job_url in seen:
                    continue
                seen.add(job_url)
                jobs.append({
                    "collected_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                    "keyword_matched": keyword,
                    "title": item.get("title", ""),
                    "company": item.get("company_name", ""),
                    "category": item.get("category", ""),
                    "job_type": item.get("job_type", ""),
                    "publication_date": item.get("publication_date", ""),
                    "candidate_location": item.get("candidate_required_location", ""),
                    "url": job_url,
                    "source": "Remotive public API",
                    "linkedin_search": linkedin_search_url(keyword),
                    "application_status": "Not applied",
                })
        except Exception as exc:
            errors.append(f"{keyword}: {exc}")

    jobs.sort(key=lambda row: row.get("publication_date", ""), reverse=True)
    csv_path = OUT / "jobs.csv"
    fields = [
        "collected_utc", "keyword_matched", "title", "company", "category",
        "job_type", "publication_date", "candidate_location", "url", "source",
        "linkedin_search", "application_status"
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(jobs)

    comments = """RECRUITER COMMENT DRAFTS — review and personalize before posting

1. Thanks for sharing this opportunity. I’m exploring roles in IT support and software development and would appreciate any guidance on the application process.

2. Thank you for posting this role. The opportunity looks relevant to my IT/technical support interests. I’ll review the requirements and apply through the official channel if there’s a match.

3. Appreciate you sharing this opening. I’m interested in learning more about the role and the skills your team values most.

Reminder: Do not paste the same generic comment repeatedly. Only comment when relevant, personalize it, and post manually.
"""
    (OUT / "recruiter_comment_drafts.txt").write_text(comments, encoding="utf-8")

    report = [
        f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Unique remote jobs collected: {len(jobs)}",
        "Source: Remotive public API (remote roles only; not a complete job-market feed).",
        "LinkedIn searches are included as links; LinkedIn itself is not scraped.",
        "Applications and comments are not submitted automatically.",
    ]
    if errors:
        report += ["", "Some searches failed:", *errors]
    (OUT / "summary.txt").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))

if __name__ == "__main__":
    main()
