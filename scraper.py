import json
import time
import os
import datetime
from playwright.sync_api import sync_playwright

BASE_URL = "https://jobs.gauteng.gov.za/Public/DepartmentJobs.aspx?dept=6"

def scrape_details(browser, link):
    """Scrapes details from a specific job link using a new page."""
    page = browser.new_page()
    details = {}
    try:
        page.goto(link, timeout=60000)
        
        # Robust Selectors based on ID attributes
        selectors = {
            'title': '#body_lblDesc',
            'reference_number': '#body_lblRefNo',
            'directorate': '#body_lblDirectorate',
            'centre': '#body_lblCentre',
            'package_detail': '#body_lblPackage',
            'closing_date_detail': '#body_lblClosingDate',
            'enquiries': '#body_lblEnquiries',
            'requirements': '#body_lblRequirements',
            'duties': '#body_lblDuties',
            'notes': '#body_lblNotes'
        }

        for key, selector in selectors.items():
            try:
                elem = page.locator(selector)
                if elem.count() > 0:
                    details[key] = elem.first.inner_text().strip()
                else:
                    details[key] = ""
            except:
                details[key] = ""

        # Also capture everything as fallback
        try:
            form = page.locator("form#form1")
            details['full_text'] = form.inner_text().strip()
        except:
            details['full_text'] = page.locator("body").inner_text().strip()
            
    except Exception as e:
        print(f"Error scraping details {link}: {e}")
        details['error'] = str(e)
    finally:
        page.close()
        
    return details

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        # Create timestamped directory
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = os.path.join("data", timestamp)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "gauteng_jobs.json")
        page = context.new_page()

        print(f"Navigating to {BASE_URL}...")
        page.goto(BASE_URL, timeout=60000)
        
        # Wait for table to load
        try:
            page.wait_for_selector("table#tblJobs", timeout=30000)
        except:
            print("Job table not found.")
            return

        all_jobs = []
        page_num = 1
        
        while True:
            print(f"Processing Page {page_num}...")
            
            # Ensure rows are present
            rows = page.locator("table#tblJobs tbody tr")
            count = rows.count()
            print(f"Found {count} jobs on this page.")
            
            if count == 0:
                break
                
            # Iterate over rows
            # Note: We extract data first to minimize interacting with the page loop
            current_page_jobs = []
            for i in range(count):
                row = rows.nth(i)
                try:
                    cols = row.locator("td")
                    if cols.count() < 5:
                        continue
                        
                    job_summary = {
                        "position": cols.nth(0).inner_text().strip(),
                        "location": cols.nth(1).inner_text().strip(),
                        "package": cols.nth(2).inner_text().strip(),
                        "closing_date": cols.nth(3).inner_text().strip(),
                    }
                    
                    # Get View Link
                    view_link_elem = row.locator("a[href^='ViewJob.aspx']")
                    if view_link_elem.count() > 0:
                        href = view_link_elem.get_attribute("href")
                        # Construct full URL
                        full_link = "https://jobs.gauteng.gov.za/Public/" + href
                        job_summary['link'] = full_link
                    else:
                        job_summary['link'] = None
                        
                    current_page_jobs.append(job_summary)
                except Exception as e:
                    print(f"Error extracting row {i}: {e}")

            # Now scrape details for each job found on this page
            # We use the 'browser' object (from context.browser) passed to helper to open new tabs
            # preventing interference with the main list page state
            for job in current_page_jobs:
                if job['link']:
                    print(f"  Scraping details for: {job['position']}")
                    details = scrape_details(context, job['link'])
                    job.update(details)
                all_jobs.append(job)

            # Pagination Logic
            # Check for 'Next' button
            next_btn = page.locator("#tblJobs_next")
            if next_btn.count() > 0 and not "disabled" in next_btn.get_attribute("class"):
                print("Clicking Next...")
                next_btn.click()
                page_num += 1
                # Wait for table update - simplistic check, wait for processing
                try:
                    # DataTables usually adds a 'processing' div or updates the 'start' index
                    # Safe wait:
                    time.sleep(2) 
                    page.wait_for_selector("table#tblJobs tbody tr", timeout=10000)
                except:
                    print("Timeout waiting for next page.")
                    break
            else:
                print("No more pages.")
                break
                
            # Save incrementally
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(all_jobs, f, indent=2, default=str)
                
    print(f"Done. Scraped {len(all_jobs)} jobs.")

if __name__ == "__main__":
    run()
