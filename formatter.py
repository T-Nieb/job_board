import json
import csv
import datetime
import os

def get_latest_data_dir(base_dir="data"):
    if not os.path.exists(base_dir):
        return None
    dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    if not dirs:
        return None
    dirs.sort(reverse=True)
    return os.path.join(base_dir, dirs[0])

def run():
    latest_dir = get_latest_data_dir()
    if not latest_dir:
        print("Error: No data folders found in 'data/'. Run scraper.py first.")
        return

    input_file = os.path.join(latest_dir, 'gauteng_jobs.json')
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    print(f"Reading from: {input_file}")
    with open(input_file, 'r') as f:
        jobs = json.load(f)
    
    # Define headers
    headers = [
        "position", 
        "reference_number", 
        "location", 
        "closing_date", 
        "package",
        "requirements",
        "duties",
        "enquiries",
        "link"
    ]
    
    today = datetime.date.today().isoformat()
    output_filename = os.path.join(latest_dir, f"gauteng_jobs_{today}.csv")
    
    try:
        with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            for job in jobs:
                # Ensure only header fields are written and handle missing keys
                row = {k: job.get(k, "") for k in headers}
                writer.writerow(row)
        
        print(f"Successfully converted {len(jobs)} jobs to CSV.")
        print(f"Output saved to: {output_filename}")
        
    except Exception as e:
        print(f"Error writing CSV: {e}")

if __name__ == "__main__":
    run()
