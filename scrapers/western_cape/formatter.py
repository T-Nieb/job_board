import json
import re
import csv
import datetime
import os

def parse_job(job):
    text = job.get('full_text', '')
    parsed = {}

    # Helper to extract sections by finding a Header, then reading until next empty line or specific stop
    def extract_section(header):
        # Look for Header followed by colon, then content
        pattern = re.compile(re.escape(header) + r":\s*(.*?)(?=\n\s*\n|\n[A-Z][a-z]+:|$)", re.DOTALL | re.IGNORECASE)
        match = pattern.search(text)
        if match:
            # Clean up: replace newlines with spaces for CSV safety/readability
            return re.sub(r'\s+', ' ', match.group(1).strip())
        return ""

    def parse_date_to_iso(date_str):
        if not date_str:
            return None
        # Try to find a date pattern like D/M/YYYY or DD/MM/YYYY
        match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
        if match:
            d, m, y = match.groups()
            try:
                # Assuming D/M/YYYY as common in SA
                return f"{y}-{int(m):02d}-{int(d):02d}"
            except ValueError:
                return date_str
        return date_str

    parsed['Title'] = "Unknown"
    # Title extraction fallback (line before Ref No or Employment Type)
    if "Employment Type:" in text:
        parts = text.split("Employment Type:")[0].split('\n')
        # Filter empty lines
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) >= 1:
            parsed['Title'] = parts[-1]

    # Reference Number extraction (stops at first space or newline)
    ref_match = re.search(r"Reference No:\s*([^\s\n]+)", text, re.IGNORECASE)
    parsed['Reference Number'] = ref_match.group(1) if ref_match else "Unknown"
    
    # Location logic
    ref_idx = text.find("Reference No:")
    parsed['Location'] = "Unknown"
    if ref_idx != -1:
        newline_idx = text.find('\n', ref_idx)
        if newline_idx != -1:
            next_line_end = text.find('\n', newline_idx + 1)
            candidate = text[newline_idx+1:next_line_end].strip()
            if candidate:
                parsed['Location'] = candidate

    parsed['Closing Date'] = parse_date_to_iso(extract_section("Closing date"))
    parsed['Posting Date'] = parse_date_to_iso(extract_section("Starting Date"))
    parsed['Minimum Educational Qualification'] = extract_section("Minimum Educational Qualification")
    parsed['Inherent Requirements'] = extract_section("Inherent Requirements Of The Job")
    parsed['Duties'] = extract_section("Duties (Key Result Areas/Outputs)")
    parsed['Enquiries'] = extract_section("Enquiries")
    parsed['Remuneration'] = extract_section("Remuneration")
    parsed['Employment Type'] = extract_section("Employment Type")
    parsed['Province'] = "Western Cape"
    # parsed['Full Text'] = text # Removed as requested
    
    return parsed

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

    input_file = os.path.join(latest_dir, 'jobs.json')
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    print(f"Reading from: {input_file}")
    with open(input_file, 'r') as f:
        jobs = json.load(f)
    
    parsed_jobs = [parse_job(j) for j in jobs]
    
    # Define headers
    headers = [
        "Title", "Reference Number", "Location", "Closing Date", "Posting Date",
        "Minimum Educational Qualification", "Inherent Requirements", "Duties",
        "Enquiries", "Remuneration", "Employment Type", "Province"
    ]
    
    # Generate Filename with current date
    today = datetime.date.today().isoformat() # YYYY-MM-DD
    output_filename = os.path.join(latest_dir, f"jobs_{today}.csv")
    
    try:
        with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            for job in parsed_jobs:
                writer.writerow(job)
        
        print(f"Successfully converted {len(parsed_jobs)} jobs to CSV.")
        print(f"Output saved to: {output_filename}")
        
    except Exception as e:
        print(f"Error writing CSV: {e}")

if __name__ == "__main__":
    run()
