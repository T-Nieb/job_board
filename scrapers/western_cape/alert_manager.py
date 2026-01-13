import json
import os
import requests
import datetime
import scraper

# Configuration
SEEN_JOBS_FILE = "seen_jobs.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def load_seen_jobs():
    """Loads the list of previously seen job reference numbers."""
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen_jobs(seen_jobs):
    """Saves the updated list of seen job reference numbers."""
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen_jobs), f, indent=2)

def send_discord_alert(job):
    """Sends a notification to Discord."""
    if not DISCORD_WEBHOOK_URL:
        print(f"Alert: New Job Found - {job.get('title')} ({job.get('reference_number')})")
        return

    embed = {
        "title": job.get('title') or "New Vacancy",
        "url": job.get('job_url'),
        "color": 3066993,  # Green-ish
        "fields": [
            {
                "name": "Reference Number",
                "value": job.get('reference_number') or "N/A",
                "inline": True
            },
            {
                "name": "Location",
                "value": job.get('location') or "Unknown",
                "inline": True
            },
            {
                "name": "Date Found",
                "value": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "inline": False
            }
        ],
        "footer": {
            "text": "Western Cape Health Scraper"
        }
    }

    payload = {
        "embeds": [embed]
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print(f"Sent Discord alert for {job.get('reference_number')}")
    except Exception as e:
        print(f"Failed to send Discord alert: {e}")

def main():
    print("Starting Alert Manager...")
    
    # 1. Load seen jobs
    seen_ids = load_seen_jobs()
    print(f"Loaded {len(seen_ids)} previously seen jobs.")

    # 2. Run Scraper
    print("Running scraper...")
    current_jobs = scraper.run()
    print(f"Scraper returned {len(current_jobs)} jobs.")

    new_jobs_count = 0
    
    # 3. Compare and Alert
    for job in current_jobs:
        # Use Reference Number as ID, fallback to Title+Location if missing
        job_id = job.get('reference_number')
        if not job_id:
            # Fallback for jobs without ref number
            job_id = f"{job.get('title')}-{job.get('location')}"
        
        if job_id not in seen_ids:
            new_jobs_count += 1
            print(f"New Job Found: {job_id}")
            send_discord_alert(job)
            seen_ids.add(job_id)
    
    # 4. Update seen list
    if new_jobs_count > 0:
        save_seen_jobs(seen_ids)
        print(f"Updated seen jobs list. {new_jobs_count} new jobs added.")
    else:
        print("No new jobs found.")

if __name__ == "__main__":
    main()
