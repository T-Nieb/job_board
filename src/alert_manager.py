import json
import os
import argparse
import datetime
import requests
import sys

# Add src to path if needed (though running as module is better)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scrapers import western_cape, gauteng, mpumalanga

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
        'color': 128, # Navy Blue
    },
    'mpumalanga': {
        'scraper': mpumalanga,
        'name': 'Mpumalanga Health',
        'state_file': 'data/state/mpumalanga_seen.json',
        'color': 15844367, # Gold/Yellow
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

def send_new_jobs_summary(new_jobs, config):
    """Sends a summary of new jobs to Discord."""
    if not new_jobs:
        return

    count = len(new_jobs)
    
    if not DISCORD_WEBHOOK_URL:
        # Dry run log
        print(f"Summary: Found {count} new jobs.")
        for job in new_jobs:
             title = job.get('title') or job.get('position') or "New Vacancy"
             print(f" - {title}")
        return

    # Build description
    lines = []
    # Limit to 15 jobs in the list to avoid hitting Discord limits
    display_limit = 15
    for i, job in enumerate(new_jobs[:display_limit]):
        title = job.get('title') or job.get('position') or "New Vacancy"
        link = job.get('job_url') or job.get('link') or "#"
        location = job.get('location') or ""
        
        # Escape markdown characters in title if needed, but keeping it simple for now
        line = f"• [{title}]({link})"
        if location and location != "Unknown":
            line += f" - {location}"
        lines.append(line)
        
    if count > display_limit:
        lines.append(f"\n... and {count - display_limit} more.")

    description = "\n".join(lines)

    embed = {
        "title": f"🚨 {count} New Jobs Found - {config['name']}",
        "description": description,
        "color": config['color'],
        "footer": {
            "text": f"{config['name']} Scraper • {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        }
    }

    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
        print(f"Sent summary alert for {count} jobs.")
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
    parser.add_argument("--province", required=True, choices=['western_cape', 'gauteng', 'mpumalanga'], help="Province to scrape")
    args = parser.parse_args()

    config = PROVINCE_CONFIG[args.province]
    print(f"Starting Alert Manager for {config['name']}...")

    # 1. Load State
    seen_ids = load_seen_jobs(config['state_file'])
    print(f"Loaded {len(seen_ids)} previously seen jobs.")

    # 2. Run Scraper
    print("Running scraper...")
    # Pass seen_ids to allow scrapers to skip existing jobs
    current_jobs = config['scraper'].run()
    print(f"Scraper returned {len(current_jobs)} jobs.")

    new_jobs_count = 0
    new_jobs_found = []

    # 3. Process Jobs
    for job in current_jobs:
        # Determine Unique ID based on province strategy
        if args.province == 'gauteng':
             # Use Link as primary ID for Gauteng
             job_id = job.get('link') or job.get('job_url')
        else:
             # Use Reference Number for Western Cape if available
             job_id = job.get('reference_number')
             if not job_id:
                  # Fallback to Title-Location
                  t = job.get('title') or job.get('position') or "Unknown"
                  l = job.get('location') or "Unknown"
                  job_id = f"{t}-{l}"
        
        if not job_id:
             # Last resort
             job_id = str(job)

        if job_id not in seen_ids:
            new_jobs_count += 1
            print(f"New Job Found: {job_id}")
            new_jobs_found.append(job)
            seen_ids.add(job_id)
            
    # 4. Send Summary Alert
    if new_jobs_found:
        send_new_jobs_summary(new_jobs_found, config)

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
