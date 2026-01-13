import json
import os
import argparse
import datetime
import requests
import sys

# Add src to path if needed (though running as module is better)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scrapers import western_cape, gauteng

# Configuration
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
DAILY_SUMMARY = os.environ.get("DAILY_SUMMARY") == "true"

PROVINCE_CONFIG = {
    'western_cape': {
        'scraper': western_cape,
        'name': 'Western Cape Health',
        'state_file': 'data/state/western_cape_seen.json',
        'color': 3066993, # Green-ish
    },
    'gauteng': {
        'scraper': gauteng,
        'name': 'Gauteng Health',
        'state_file': 'data/state/gauteng_seen.json',
        'color': 3066993,
    }
}

def load_seen_jobs(filepath):
    """Loads the list of previously seen job identifiers."""
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return set(json.load(f))
    return set()

def save_seen_jobs(filepath, seen_jobs):
    """Saves the updated list of seen job identifiers."""
    # Ensure dir exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(list(seen_jobs), f, indent=2)

def send_discord_alert(job, config):
    """Sends a notification to Discord."""
    if not DISCORD_WEBHOOK_URL:
        # Dry run log
        title = job.get('title') or job.get('position') or "New Vacancy"
        ref = job.get('reference_number') or "N/A"
        print(f"Alert: New Job Found - {title} ({ref})")
        return

    # Normalize fields (WC vs Gauteng differences)
    title = job.get('title') or job.get('position') or "New Vacancy"
    ref = job.get('reference_number') or "N/A"
    link = job.get('job_url') or job.get('link')
    location = job.get('location') or "Unknown"

    embed = {
        "title": title,
        "url": link,
        "color": config['color'],
        "fields": [
            {
                "name": "Reference Number",
                "value": ref,
                "inline": True
            },
            {
                "name": "Location",
                "value": location,
                "inline": True
            },
            {
                "name": "Date Found",
                "value": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "inline": False
            }
        ],
        "footer": {
            "text": f"{config['name']} Scraper"
        }
    }

    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
        print(f"Sent Discord alert for {ref}")
    except Exception as e:
        print(f"Failed to send Discord alert: {e}")

def send_daily_summary(job_count, config):
    """Sends a daily summary status report."""
    if not DISCORD_WEBHOOK_URL:
        print(f"Daily Summary for {config['name']}: {job_count} jobs.")
        return

    message = f"**Daily Status Report ({config['name']})**\nThere are currently **{job_count}** vacancies listed."
    if job_count == 0:
        message = f"**Daily Status Report ({config['name']})**\nNo vacancies are currently available."
        color = 15158332 # Red
    else:
        color = config['color']

    embed = {
        "title": f"Daily Job Summary - {config['name']}",
        "description": message,
        "color": color,
        "footer": {
            "text": f"{config['name']} Scraper"
        },
        "timestamp": datetime.datetime.now().isoformat()
    }

    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
        print("Sent Daily Summary.")
    except Exception as e:
        print(f"Failed to send summary: {e}")

def main():
    parser = argparse.ArgumentParser(description="Run Job Alerts")
    parser.add_argument("--province", required=True, choices=['western_cape', 'gauteng'], help="Province to scrape")
    args = parser.parse_args()

    config = PROVINCE_CONFIG[args.province]
    print(f"Starting Alert Manager for {config['name']}...")

    # 1. Load State
    seen_ids = load_seen_jobs(config['state_file'])
    print(f"Loaded {len(seen_ids)} previously seen jobs.")

    # 2. Run Scraper
    print("Running scraper...")
    # Scrapers are expected to return a list of dicts
    current_jobs = config['scraper'].run()
    print(f"Scraper returned {len(current_jobs)} jobs.")

    new_jobs_count = 0

    # 3. Process Jobs
    for job in current_jobs:
        # Determine Unique ID
        job_id = job.get('reference_number')
        if not job_id:
             job_id = job.get('link') # Gauteng fallback
        if not job_id:
             # Last resort composite
             title = job.get('title') or job.get('position') or "Unknown"
             loc = job.get('location') or "Unknown"
             job_id = f"{title}-{loc}"
        
        if job_id not in seen_ids:
            new_jobs_count += 1
            print(f"New Job Found: {job_id}")
            send_discord_alert(job, config)
            seen_ids.add(job_id)

    # 4. Save State
    if new_jobs_count > 0:
        save_seen_jobs(config['state_file'], seen_ids)
        print(f"Updated seen jobs list. {new_jobs_count} new jobs added.")
    else:
        print("No new jobs found.")

    # 5. Daily Summary
    if DAILY_SUMMARY:
        send_daily_summary(len(current_jobs), config)

if __name__ == "__main__":
    main()
